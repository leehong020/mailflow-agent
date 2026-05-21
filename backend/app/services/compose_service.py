"""主动写邮件业务服务。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.compose_mail_agent import ComposeMailAgent
from app.models.draft import DraftPreview
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.memory_service import MemoryService
from app.services.trace_service import TraceService


class ComposeService:
    """第十二阶段 Compose Mail 服务。

    该服务只负责“生成/修改本地草稿”。真正发送邮件仍然复用 DraftService 的
    send-action 流程，从而继续满足 Human-in-the-loop 的安全要求。
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.trace_service = TraceService(db)
        self.memory_service = MemoryService(db)
        self.compose_agent = ComposeMailAgent()

    def generate_preview(
        self,
        *,
        goal: str,
        to: str = "",
        subject: str = "",
        body: str = "",
        tone: str = "polite",
        language: str = "auto",
    ) -> tuple[DraftPreview, str]:
        """调用 ComposeMailAgent 生成主动写邮件草稿，并保存到 DraftPreview。"""

        user = self._current_user()
        trace = self.trace_service.create_trace(
            user=user,
            task_type="compose_mail",
            input_summary=goal[:240],
        )
        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="ComposeMailAgent",
            status="running",
            message="开始根据写信目标生成邮件草稿。",
            input_preview=goal[:500],
        )

        result = self.compose_agent.generate(
            goal=goal,
            to=to,
            subject=subject,
            body=body,
            tone=tone,
            language=language,
        )
        preview = DraftPreview(
            user_id=user.id,
            source_email_id="",
            to=result.to.strip(),
            subject=result.subject.strip() or "(无主题)",
            body=result.body,
            tone=tone,
            language=language,
            generation_reason=result.generation_reason,
        )
        self.db.add(preview)
        self.db.flush()

        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="ComposeMailAgent",
            status="completed",
            message="主动写邮件草稿生成完成。",
            output_preview=f"{preview.subject}\n{preview.body[:300]}",
        )
        self.trace_service.complete_trace(trace, output_summary=f"已生成草稿：{preview.subject}")
        return preview, trace.id

    def revise_preview(
        self,
        preview_id: str,
        *,
        instruction: str,
        to: str,
        subject: str,
        body: str,
        tone: str = "polite",
        language: str = "auto",
    ) -> tuple[DraftPreview, str]:
        """调用 ComposeMailAgent 修改已有主动写邮件草稿。"""

        user = self._current_user()
        preview = self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == preview_id, DraftPreview.user_id == user.id)
        ).first()
        if preview is None:
            raise ValueError("草稿不存在。")

        trace = self.trace_service.create_trace(
            user=user,
            task_type="compose_mail_revise",
            input_summary=instruction[:240],
        )
        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="ComposeMailAgent",
            status="running",
            message="开始根据用户要求修改主动写邮件草稿。",
            input_preview=instruction[:500],
        )

        memory_context = self.memory_service.context_for_draft(draft_preview_id=preview.id)
        final_instruction = instruction
        if memory_context:
            final_instruction = f"{instruction}\n\n当前草稿此前右侧 AI 对话记忆：\n{memory_context}"

        result = self.compose_agent.revise(
            instruction=final_instruction,
            to=to,
            subject=subject,
            body=body,
            tone=tone,
            language=language,
        )
        preview.to = result.to.strip()
        preview.subject = result.subject.strip() or subject or "(无主题)"
        preview.body = result.body
        preview.tone = tone
        preview.language = language
        preview.generation_reason = result.generation_reason
        self.db.flush()

        self.trace_service.add_event(
            trace=trace,
            step=1,
            agent_name="ComposeMailAgent",
            status="completed",
            message="主动写邮件草稿修改完成。",
            output_preview=f"{preview.subject}\n{preview.body[:300]}",
        )
        self.trace_service.complete_trace(trace, output_summary=f"已修改草稿：{preview.subject}")
        return preview, trace.id

    def _current_user(self) -> User:
        """读取当前已连接 Google 的本地用户。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user
