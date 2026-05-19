"""邮件同步与分析服务。

第三阶段的核心业务服务：
1. 从 Gmail 拉取最近邮件；
2. 保存到 email_records；
3. 执行 EmailAnalysisGraph；
4. 将摘要、分类、任务写入数据库；
5. 为前端 Inbox 看板和邮件详情页提供查询能力。
"""

from datetime import datetime

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.graphs.email_analysis_graph import EmailAnalysisGraph, EmailAnalysisGraphResult
from app.models.email import EmailAnalysis, EmailRecord, TaskItem
from app.models.trace import AgentTrace
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService
from app.services.trace_service import TraceService


class EmailAnalysisService:
    """邮件分析业务服务。"""

    def __init__(self, db: Session) -> None:
        # Service 层持有数据库会话和下游服务，路由层只负责参数与 HTTP 状态码。
        self.db = db
        self.auth_service = AuthService(db)
        self.google_service = GoogleService(db)
        self.graph = EmailAnalysisGraph()
        self.trace_service = TraceService(db)

    def sync_recent_emails(self, limit: int = 20) -> list[EmailRecord]:
        """从 Gmail 同步最近邮件到本地数据库。"""

        user = self._current_user()
        # GoogleService 会负责 token 解密、刷新和 Gmail API 调用。
        raw_emails = self.google_service.list_recent_emails(limit=limit)
        new_records: list[EmailRecord] = []

        for raw in raw_emails:
            record, created = self._upsert_email(user=user, raw=raw)
            if created:
                new_records.append(record)

        self.db.commit()
        return new_records

    def analyze_recent_emails(self, limit: int = 20) -> int:
        """同步并分析最近邮件，仅处理新增邮件。"""

        # 只分析本次同步中新出现的邮件，避免重复消耗模型 token。
        records = self.sync_recent_emails(limit=limit)
        for record in records:
            self.analyze_email(record)
        self.db.commit()
        return len(records)

    def analyze_unanalyzed_emails(self, limit: int = 20) -> int:
        """同步 Gmail 后，分析本地数据库中尚未有分析结果的邮件。

        Inbox 页面按钮叫“同步并分析邮件”，因此这里先拉取 Gmail 最近邮件，
        再查询没有 EmailAnalysis 的本地记录。这样第一次使用时不会因为本地
        没有邮件而显示空列表。
        """

        user = self._current_user()
        self.sync_recent_emails(limit=limit)
        records = self.db.scalars(
            select(EmailRecord)
            .where(EmailRecord.user_id == user.id)
            # analysis 是 ORM relationship，不是普通数据库列。
            # 判断“尚未有关联分析结果”要使用 has()，不能写成
            # EmailRecord.analysis.is_(None)，否则 SQLAlchemy 会把 relationship
            # comparator 的内部函数暴露成异常信息。
            .where(~EmailRecord.analysis.has())
            .order_by(EmailRecord.received_at.desc().nullslast())
            .limit(limit)
        ).all()
        for record in records:
            self.analyze_email(record)
        self.db.commit()
        return len(records)

    def reanalyze_email(self, email: EmailRecord) -> EmailAnalysis:
        """强制重新分析单封邮件。"""

        existing_analysis = email.analysis
        result = self.graph.run(email)
        if existing_analysis is not None and not self._analysis_is_degraded(existing_analysis):
            if self._result_is_degraded(result):
                # 重新分析依赖外部 LLM。模型临时不可用或输出不合规时，Agent 会
                # 返回降级结果。此时不能把数据库中已有的高质量分析覆盖掉，
                # 否则用户会看到“之前有分析，重新分析后反而变差/消失”。
                return existing_analysis
        return self._save_analysis(email=email, result=result)

    def _save_analysis(self, *, email: EmailRecord, result: EmailAnalysisGraphResult) -> EmailAnalysis:
        """把 Agent 输出写入数据库。"""

        analysis = email.analysis
        if analysis is None:
            analysis = EmailAnalysis(email_id=email.id)
            self.db.add(analysis)

        analysis.summary = result.summary.summary
        analysis.key_points = result.summary.key_points
        analysis.category = result.triage.category
        analysis.priority = result.triage.priority
        analysis.need_reply = result.triage.need_reply
        analysis.has_task = result.triage.has_task
        analysis.has_meeting_request = result.triage.has_meeting_request
        analysis.reason = result.triage.reason
        analysis.recommended_actions = result.triage.recommended_actions
        self.db.flush()

        self.db.execute(delete(TaskItem).where(TaskItem.source_email_id == email.id))
        for task in result.tasks:
            self.db.add(
                TaskItem(
                    user_id=email.user_id,
                    source_email_id=email.id,
                    title=task.title,
                    description=task.description,
                    deadline=task.deadline,
                    priority=task.priority,
                )
            )
        return analysis

    @staticmethod
    def _result_is_degraded(result: EmailAnalysisGraphResult) -> bool:
        """判断本次 Agent 结果是否来自降级兜底。"""

        return (
            result.summary.summary.startswith("模型输出校验或调用失败")
            or result.triage.reason.startswith("模型输出校验或调用失败")
        )

    @staticmethod
    def _analysis_is_degraded(analysis: EmailAnalysis) -> bool:
        """判断数据库里的分析是否已经是降级结果。"""

        return (
            analysis.summary.startswith("模型输出校验或调用失败")
            or analysis.reason.startswith("模型输出校验或调用失败")
        )

    def analyze_email(self, email: EmailRecord) -> EmailAnalysis:
        """运行三个 Agent，并保存分析结果。"""

        # EmailAnalysisGraph 内部会依次调用三个大模型 Agent。
        user = self._current_user()
        trace = self.trace_service.create_trace(
            user=user,
            task_type="analyze_email",
            input_summary=f"邮件：{email.subject} | {email.sender}",
        )
        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="EmailSummarizerAgent",
            status="running",
            message="开始生成邮件摘要。",
            input_preview=(email.subject or "")[:120],
        )
        summary = self.graph.summarizer.summarize(email)
        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="EmailSummarizerAgent",
            status="completed",
            message="邮件摘要生成完成。",
            output_preview=summary.summary[:200],
        )

        self.trace_service.add_event(
            trace=trace,
            step=2,
            agent_name="EmailTriageAgent",
            status="running",
            message="开始判断邮件分类与优先级。",
            input_preview=(email.subject or "")[:120],
        )
        triage = self.graph.triage_agent.triage(email)
        self.trace_service.add_event(
            trace=trace,
            step=2,
            agent_name="EmailTriageAgent",
            status="completed",
            message="邮件分类完成。",
            output_preview=f"{triage.category} / {triage.priority}",
        )

        self.trace_service.add_event(
            trace=trace,
            step=3,
            agent_name="TaskExtractionAgent",
            status="running",
            message="开始提取待办事项。",
            input_preview=(email.subject or "")[:120],
        )
        tasks = self.graph.task_agent.extract(email=email, has_task=triage.has_task, priority=triage.priority)
        self.trace_service.add_event(
            trace=trace,
            step=3,
            agent_name="TaskExtractionAgent",
            status="completed",
            message="待办事项提取完成。",
            output_preview=f"提取到 {len(tasks)} 个任务。",
        )

        result = EmailAnalysisGraphResult(summary=summary, triage=triage, tasks=tasks)
        analysis = self._save_analysis(email=email, result=result)
        self.trace_service.complete_trace(trace, output_summary=f"完成分析：{triage.category} / {triage.priority}")
        return analysis

    def list_emails(
        self,
        *,
        category: str | None = None,
        priority: str | None = None,
        need_reply: bool | None = None,
        has_meeting_request: bool | None = None,
        has_task: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[EmailRecord], int]:
        """按分类、优先级等条件查询邮件列表。"""

        user = self._current_user()
        query = self._base_query(user.id)

        # 只有用户传入分析相关筛选条件时才 join email_analysis。
        if any(value is not None for value in [category, priority, need_reply, has_meeting_request, has_task]):
            query = query.join(EmailAnalysis, EmailAnalysis.email_id == EmailRecord.id)

        if category:
            query = query.where(EmailAnalysis.category == category)
        if priority:
            query = query.where(EmailAnalysis.priority == priority)
        if need_reply is not None:
            query = query.where(EmailAnalysis.need_reply == need_reply)
        if has_meeting_request is not None:
            query = query.where(EmailAnalysis.has_meeting_request == has_meeting_request)
        if has_task is not None:
            query = query.where(EmailAnalysis.has_task == has_task)

        # total 用于前端后续分页；当前页面先展示最近 20 封。
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        records = self.db.scalars(
            query.order_by(EmailRecord.received_at.desc().nullslast()).offset(offset).limit(limit)
        ).unique().all()
        return list(records), total

    def get_email_detail(self, email_id: str) -> EmailRecord | None:
        """查询邮件详情，包含分析结果和任务。"""

        user = self._current_user()
        record = self.db.scalars(
            select(EmailRecord)
            .options(joinedload(EmailRecord.analysis), joinedload(EmailRecord.tasks))
            .where(EmailRecord.user_id == user.id, EmailRecord.id == email_id)
        ).unique().first()
        if record is not None:
            return record

        # 开发阶段用户可能会断开 Google 后重新授权。旧用户被删除后，浏览器里
        # 仍可能停留在旧 EmailRecord 的详情 URL 上。此时不要直接让前端显示
        # “尚未分析”，而是根据同一个 Gmail message id 找到当前用户重新同步
        # 后的那条记录，并返回它已经保存的分析结果。
        stale_record = self.db.scalars(select(EmailRecord).where(EmailRecord.id == email_id)).first()
        if stale_record is None:
            return None
        return self.db.scalars(
            select(EmailRecord)
            .options(joinedload(EmailRecord.analysis), joinedload(EmailRecord.tasks))
            .where(
                EmailRecord.user_id == user.id,
                EmailRecord.gmail_message_id == stale_record.gmail_message_id,
            )
        ).unique().first()

    def _current_user(self) -> User:
        """获取当前连接的 Google 用户。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user

    @staticmethod
    def _base_query(user_id: str) -> Select[tuple[EmailRecord]]:
        """邮件查询基础语句，统一预加载分析结果和任务。"""

        return (
            select(EmailRecord)
            .options(joinedload(EmailRecord.analysis), joinedload(EmailRecord.tasks))
            .where(EmailRecord.user_id == user_id)
        )

    def _upsert_email(self, *, user: User, raw: dict) -> tuple[EmailRecord, bool]:
        """保存或更新 Gmail 邮件，返回是否为新插入记录。"""

        record = self.db.scalars(
            select(EmailRecord).where(
                EmailRecord.user_id == user.id,
                EmailRecord.gmail_message_id == raw["id"],
            )
        ).first()
        created = False
        if record is None:
            record = EmailRecord(user_id=user.id, gmail_message_id=raw["id"])
            self.db.add(record)
            created = True

        # 同一封 Gmail 邮件重复同步时，只刷新本地展示字段，不重新进入分析。
        record.thread_id = raw.get("thread_id")
        record.subject = raw.get("subject") or "(无主题)"
        record.sender = raw.get("sender") or ""
        record.recipients = raw.get("recipients") or []
        record.received_at = self._parse_datetime(raw.get("received_at"))
        record.body_text = raw.get("body_text") or raw.get("body_preview") or ""
        record.snippet = raw.get("snippet") or ""
        return record, created

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """把 Gmail 返回的 ISO 时间转换为 datetime，解析失败时返回 None。"""

        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
