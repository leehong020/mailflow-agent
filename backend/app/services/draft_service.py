"""第五阶段回复草稿服务。

第七阶段之后，确认/拒绝外部操作统一交给 ActionService。
DraftService 保留草稿预览能力，并负责把草稿提交到待确认中心。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.reply_draft_agent import ReplyDraftAgent
from app.models.draft import DraftPreview, PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.action_service import ActionService
from app.services.auth_service import AuthService
from app.services.memory_service import MemoryService


class DraftService:
    """回复草稿与确认操作业务服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.action_service = ActionService(db)
        self.memory_service = MemoryService(db)
        self.reply_draft_agent = ReplyDraftAgent()

    def list_previews(self, *, limit: int = 20, offset: int = 0) -> tuple[list[DraftPreview], int]:
        """查询当前用户的草稿预览列表。"""

        user = self._current_user()
        query = select(DraftPreview).where(DraftPreview.user_id == user.id).order_by(DraftPreview.created_at.desc())
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.offset(offset).limit(limit)).all()
        return list(items), total

    def get_preview(self, preview_id: str) -> DraftPreview | None:
        """查询单个草稿预览。"""

        user = self._current_user()
        return self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == preview_id, DraftPreview.user_id == user.id)
        ).first()

    def get_latest_preview(self, email_id: str) -> DraftPreview | None:
        user = self._current_user()
        return self.db.scalars(
            select(DraftPreview)
            .where(DraftPreview.user_id == user.id, DraftPreview.source_email_id == email_id)
            .order_by(DraftPreview.created_at.desc())
        ).first()

    def create_reply_workspace_preview(self, *, email: EmailRecord) -> DraftPreview:
        """为 AI 回复工作台创建一个空白回复草稿壳。

        这个方法不会直接调用 ReplyDraftAgent 生成完整回复，而是先创建一个
        结构化草稿容器，让前端可以进入“左侧编辑器 + 右侧 AI 对话”模式。
        这样做的好处是：
        1. 用户可以先看原邮件，再逐步让 AI 改写；
        2. 草稿会被持久化到 DraftPreview，方便 Draft Review 继续编辑；
        3. 后续的每次对话修改都能复用同一个 preview_id。
        """

        user = self._current_user()
        preview = DraftPreview(
            user_id=user.id,
            source_email_id=email.id,
            to=email.sender,
            subject=ReplyDraftAgent._subject("", email.subject),
            body="",
            tone="workspace",
            language="auto",
            generation_reason="已创建 AI 回复工作台，请在右侧输入你的回复要求来生成左侧内容。",
        )
        self.db.add(preview)
        self.db.flush()
        return preview

    def create_draft_preview(self, *, email: EmailRecord, tone: str = "polite", language: str = "en") -> DraftPreview:
        """基于单封邮件生成回复草稿预览。"""

        user = self._current_user()
        data = self.reply_draft_agent.draft(email=email, tone=tone, language=language)

        preview = DraftPreview(
            user_id=user.id,
            source_email_id=email.id,
            to=data.to,
            subject=data.subject,
            body=data.body,
            tone=tone,
            language=language,
            generation_reason=data.generation_reason,
        )
        self.db.add(preview)
        self.db.flush()
        return preview

    def create_manual_preview(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        tone: str = "manual",
        language: str = "zh",
    ) -> DraftPreview:
        """创建用户手写的新邮件草稿预览。

        该方法只写本地 DraftPreview，不调用 Gmail。用户后续可选择创建 Gmail
        草稿或发送邮件，两者都必须进入 Pending Actions。
        """

        user = self._current_user()
        preview = DraftPreview(
            user_id=user.id,
            source_email_id="",
            to=to.strip(),
            subject=subject.strip() or "(无主题)",
            body=body,
            tone=tone,
            language=language,
            generation_reason="用户手动撰写的新邮件草稿。",
        )
        self.db.add(preview)
        self.db.flush()
        return preview

    def create_forward_preview(self, *, email: EmailRecord) -> DraftPreview:
        """基于原始邮件生成可编辑的转发草稿。"""

        user = self._current_user()
        subject = email.subject if email.subject.lower().startswith("fw:") else f"Fw: {email.subject}"
        body = (
            "\n\n"
            "---------- Forwarded message ---------\n"
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n\n"
            f"{email.body_text or email.snippet}"
        )
        preview = DraftPreview(
            user_id=user.id,
            source_email_id=email.id,
            to="",
            subject=subject,
            body=body,
            tone="forward",
            language="zh",
            generation_reason="根据原邮件生成的转发草稿，发送前需要用户填写收件人并确认。",
        )
        self.db.add(preview)
        self.db.flush()
        return preview

    def update_preview(
        self,
        preview_id: str,
        *,
        tone: str,
        language: str,
        to: str | None = None,
        body: str | None = None,
        subject: str | None = None,
    ) -> DraftPreview:
        user = self._current_user()
        preview = self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == preview_id, DraftPreview.user_id == user.id)
        ).first()
        if preview is None:
            raise ValueError("草稿不存在。")
        preview.tone = tone
        preview.language = language
        if to is not None:
            preview.to = to.strip()
        if body is not None:
            preview.body = body
        if subject is not None:
            preview.subject = subject
        preview.generation_reason = "用户修改了草稿内容。"
        self.db.flush()
        return preview

    def revise_preview(
        self,
        preview_id: str,
        *,
        instruction: str,
        to: str,
        subject: str,
        body: str,
        tone: str,
        language: str,
    ) -> DraftPreview:
        """使用 ReplyDraftAgent 根据用户对话指令修改草稿。"""

        user = self._current_user()
        preview = self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == preview_id, DraftPreview.user_id == user.id)
        ).first()
        if preview is None:
            raise ValueError("草稿不存在。")
        if not instruction.strip():
            raise ValueError("请输入 AI 修改要求。")

        email = None
        if preview.source_email_id:
            email = self.db.scalars(
                select(EmailRecord).where(EmailRecord.id == preview.source_email_id, EmailRecord.user_id == user.id)
            ).first()

        memory_context = self.memory_service.context_for_draft(draft_preview_id=preview.id)
        final_instruction = instruction
        if memory_context:
            final_instruction = f"{instruction}\n\n当前草稿此前右侧 AI 对话记忆：\n{memory_context}"

        result = self.reply_draft_agent.revise(
            email=email,
            to=to,
            subject=subject,
            body=body,
            instruction=final_instruction,
            tone=tone,
            language=language,
        )
        preview.to = result.to.strip()
        preview.subject = result.subject.strip() or subject
        preview.body = result.body
        preview.tone = tone
        preview.language = language
        preview.generation_reason = result.generation_reason
        self.db.flush()
        return preview

    def delete_preview(self, preview_id: str) -> None:
        """删除草稿预览。

        正在等待确认的草稿不能直接删除，否则用户可能误以为外部操作已取消。
        已执行、已拒绝或失败的历史操作会保留 payload/preview，因此可以解除
        关联后删除本地草稿预览，不会影响 Gmail 中已经创建的真实草稿。
        """

        user = self._current_user()
        preview = self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == preview_id, DraftPreview.user_id == user.id)
        ).first()
        if preview is None:
            raise ValueError("草稿不存在。")

        linked_actions = self.db.scalars(
            select(PendingAction).where(
                PendingAction.user_id == user.id,
                PendingAction.draft_preview_id == preview.id,
            )
        ).all()
        if any(action.status == "pending" for action in linked_actions):
            raise ValueError("草稿正在待确认中，请先到 Pending Actions 确认或拒绝该操作。")

        for action in linked_actions:
            action.draft_preview_id = None
        self.db.delete(preview)
        self.db.flush()

    def create_pending_action_for_draft(self, *, draft_preview: DraftPreview) -> PendingAction:
        """把草稿放入待确认中心。"""

        user = self._current_user()
        if draft_preview.user_id != user.id:
            raise ValueError("草稿不存在。")

        handled_action = self.db.scalars(
            select(PendingAction).where(
                PendingAction.user_id == user.id,
                PendingAction.draft_preview_id == draft_preview.id,
                PendingAction.status.in_(["pending", "executed"]),
            )
        ).first()
        if handled_action:
            if handled_action.status == "pending":
                return handled_action
            raise ValueError("该草稿已经确认执行过，不能重复提交。")

        existing = self.db.scalars(
            select(PendingAction).where(
                PendingAction.user_id == user.id,
                PendingAction.draft_preview_id == draft_preview.id,
                PendingAction.status == "pending",
            )
        ).first()
        if existing:
            return existing

        payload = {
            "to": draft_preview.to,
            "subject": draft_preview.subject,
            "body": draft_preview.body,
            "tone": draft_preview.tone,
            "language": draft_preview.language,
            "source_email_id": draft_preview.source_email_id,
        }
        preview = {
            "收件人": draft_preview.to,
            "主题": draft_preview.subject,
            "正文预览": draft_preview.body[:500],
            "关联邮件": draft_preview.source_email_id,
        }
        action = self.action_service.create_action(
            action_type="create_gmail_draft",
            draft_preview_id=draft_preview.id,
            payload=payload,
            preview=preview,
        )
        draft_preview.status = "pending"
        self.db.flush()
        return action

    def create_send_action_for_draft(self, *, draft_preview: DraftPreview) -> PendingAction:
        """把草稿发送操作放入待确认中心。"""

        user = self._current_user()
        if draft_preview.user_id != user.id:
            raise ValueError("草稿不存在。")
        if not draft_preview.to.strip():
            raise ValueError("发送邮件前必须填写收件人。")
        if not draft_preview.body.strip():
            raise ValueError("发送邮件前正文不能为空。")

        handled_action = self.db.scalars(
            select(PendingAction).where(
                PendingAction.user_id == user.id,
                PendingAction.draft_preview_id == draft_preview.id,
                PendingAction.action_type == "send_email",
                PendingAction.status.in_(["pending", "executed"]),
            )
        ).first()
        if handled_action:
            if handled_action.status == "pending":
                return handled_action
            raise ValueError("该草稿已经发送过，不能重复提交。")

        payload = {
            "to": draft_preview.to,
            "subject": draft_preview.subject,
            "body": draft_preview.body,
            "source_email_id": draft_preview.source_email_id,
        }
        preview = {
            "收件人": draft_preview.to,
            "主题": draft_preview.subject,
            "正文": draft_preview.body,
            "关联邮件": draft_preview.source_email_id,
        }
        action = self.action_service.create_action(
            action_type="send_email",
            draft_preview_id=draft_preview.id,
            payload=payload,
            preview=preview,
        )
        draft_preview.status = "send_pending"
        self.db.flush()
        return action

    def create_direct_send_action(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> PendingAction:
        """直接撰写邮件并创建发送待确认操作。"""

        preview = self.create_manual_preview(to=to, subject=subject, body=body)
        return self.create_send_action_for_draft(draft_preview=preview)

    def list_pending_actions(
        self,
        *,
        status: str | None = "pending",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PendingAction], int]:
        return self.action_service.list_actions(status=status, limit=limit, offset=offset)

    def confirm_action(self, action_id: str) -> str:
        return self.action_service.confirm_action(action_id)

    def reject_action(self, action_id: str) -> None:
        self.action_service.reject_action(action_id)

    def _current_user(self) -> User:
        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user
