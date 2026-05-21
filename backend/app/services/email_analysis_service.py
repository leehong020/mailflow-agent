"""邮件同步与分析服务。

第三阶段的核心业务服务：
1. 从 Gmail 拉取最近邮件；
2. 保存到 email_records；
3. 执行 EmailAnalysisGraph；
4. 将摘要、分类、任务写入数据库；
5. 为前端 Inbox 看板和邮件详情页提供查询能力。
"""

from datetime import datetime

from sqlalchemy import Select, delete, func, or_, select
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

    def analyze_unanalyzed_emails(self, limit: int = 20) -> tuple[int, list[str]]:
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
        trace_ids: list[str] = []
        for record in records:
            _, trace = self.analyze_email(record)
            trace_ids.append(trace.id)
        self.db.commit()
        return len(records), trace_ids

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

    def analyze_email(self, email: EmailRecord) -> tuple[EmailAnalysis, AgentTrace]:
        """运行 LangGraph 邮件分析图，并保存分析结果和轨迹。"""

        user = self._current_user()
        trace = self.trace_service.create_trace(
            user=user,
            task_type="analyze_email",
            input_summary=f"邮件：{email.subject} | {email.sender}",
        )

        def trace_event(
            step: int,
            agent_name: str,
            event_status: str,
            message: str,
            input_preview: str,
            output_preview: str,
        ) -> None:
            """LangGraph 节点回调：把节点状态写入数据库，供 SSE 推送。"""

            self.trace_service.add_event(
                trace=trace,
                step=step,
                agent_name=agent_name,
                status=event_status,
                message=message,
                input_preview=input_preview,
                output_preview=output_preview,
            )
            # 分析请求仍是同步执行。这里主动 flush，让并发的 SSE 连接能尽快
            # 读到新事件，而不是等整个请求 commit 后才看到所有事件。
            self.db.flush()

        try:
            result = self.graph.run(email, on_event=trace_event)
            analysis = self._save_analysis(email=email, result=result)
            self.trace_service.complete_trace(
                trace,
                output_summary=f"完成分析：{result.triage.category} / {result.triage.priority}",
            )
            return analysis, trace
        except Exception as exc:
            self.trace_service.add_event(
                trace=trace,
                step=99,
                agent_name="EmailAnalysisGraph",
                status="failed",
                message="邮件分析工作流执行失败。",
                output_preview=str(exc)[:200],
            )
            self.trace_service.fail_trace(trace, output_summary=str(exc)[:500])
            raise

    def list_emails(
        self,
        *,
        category: str | None = None,
        priority: str | None = None,
        need_reply: bool | None = None,
        has_meeting_request: bool | None = None,
        has_task: bool | None = None,
        search: str | None = None,
        analyzed: bool | None = None,
        label: str | None = None,
        is_read: bool | None = None,
        is_starred: bool | None = None,
        mailbox_status: str | None = None,
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
        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    EmailRecord.subject.ilike(pattern),
                    EmailRecord.sender.ilike(pattern),
                    EmailRecord.snippet.ilike(pattern),
                    EmailRecord.body_text.ilike(pattern),
                )
            )
        if analyzed is True:
            query = query.where(EmailRecord.analysis.has())
        if analyzed is False:
            query = query.where(~EmailRecord.analysis.has())
        if label:
            # SQLite JSON 查询能力有限；这里用 contains 满足本地演示和 PostgreSQL JSONB 迁移前的查询需求。
            query = query.where(EmailRecord.label_ids.contains(label))
        if is_read is not None:
            query = query.where(EmailRecord.is_read.is_(is_read))
        if is_starred is not None:
            query = query.where(EmailRecord.is_starred.is_(is_starred))
        if mailbox_status:
            query = query.where(EmailRecord.mailbox_status == mailbox_status)

        # total 用于前端后续分页；当前页面先展示最近 20 封。
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        records = self.db.scalars(
            query.order_by(EmailRecord.received_at.desc().nullslast()).offset(offset).limit(limit)
        ).unique().all()
        return list(records), total

    def analysis_totals(self) -> tuple[int, int]:
        """返回当前用户已分析和未分析邮件数量，用于 Inbox 状态条。"""

        user = self._current_user()
        analyzed_total = (
            self.db.scalar(
                select(func.count())
                .select_from(EmailRecord)
                .where(EmailRecord.user_id == user.id, EmailRecord.analysis.has())
            )
            or 0
        )
        unanalyzed_total = (
            self.db.scalar(
                select(func.count())
                .select_from(EmailRecord)
                .where(EmailRecord.user_id == user.id, ~EmailRecord.analysis.has())
            )
            or 0
        )
        return analyzed_total, unanalyzed_total

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
        record.label_ids = raw.get("label_ids") or []
        record.is_read = bool(raw.get("is_read", True))
        record.is_starred = bool(raw.get("is_starred", False))
        record.mailbox_status = raw.get("mailbox_status") or "inbox"
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
