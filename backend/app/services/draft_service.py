"""第五阶段回复草稿与待确认操作服务。"""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.reply_draft_agent import ReplyDraftAgent
from app.models.calendar import CalendarSuggestion
from app.models.draft import DraftPreview, PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService


class DraftService:
    """回复草稿与确认操作业务服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.google_service = GoogleService(db)
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

    def update_preview(
        self,
        preview_id: str,
        *,
        tone: str,
        language: str,
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
        if body is not None:
            preview.body = body
        if subject is not None:
            preview.subject = subject
        preview.generation_reason = "用户修改了草稿内容。"
        self.db.flush()
        return preview

    def create_pending_action_for_draft(self, *, draft_preview: DraftPreview) -> PendingAction:
        """把草稿放入待确认中心。"""

        user = self._current_user()
        if draft_preview.user_id != user.id:
            raise ValueError("草稿不存在。")

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
        }
        action = PendingAction(
            user_id=user.id,
            action_type="create_gmail_draft",
            draft_preview_id=draft_preview.id,
            payload=json.dumps(payload, ensure_ascii=False),
            preview=json.dumps(payload, ensure_ascii=False),
            risk_level="medium",
        )
        draft_preview.status = "pending"
        self.db.add(action)
        self.db.flush()
        return action

    def list_pending_actions(
        self,
        *,
        status: str | None = "pending",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PendingAction], int]:
        user = self._current_user()
        query = select(PendingAction).where(PendingAction.user_id == user.id).order_by(PendingAction.created_at.desc())
        if status:
            query = query.where(PendingAction.status == status)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.offset(offset).limit(limit)).all()
        return list(items), total

    def confirm_action(self, action_id: str) -> str:
        user = self._current_user()
        action = self.db.scalars(
            select(PendingAction).where(PendingAction.id == action_id, PendingAction.user_id == user.id)
        ).first()
        if action is None:
            raise ValueError("待确认操作不存在。")
        if action.status != "pending":
            raise ValueError("该操作已经处理过。")
        payload = json.loads(action.payload or "{}")
        result_payload: dict
        if action.action_type == "create_gmail_draft":
            result_payload = self.google_service.create_gmail_draft(
                to=str(payload.get("to") or ""),
                subject=str(payload.get("subject") or ""),
                body=str(payload.get("body") or ""),
            )
        elif action.action_type == "create_calendar_event":
            result_payload = self.google_service.create_calendar_event(
                summary=str(payload.get("summary") or ""),
                start=str(payload.get("start") or ""),
                end=str(payload.get("end") or ""),
                attendees=list(payload.get("attendees") or []),
                description=str(payload.get("description") or ""),
                location=str(payload.get("location") or ""),
                timezone=str(payload.get("timezone") or "Asia/Shanghai"),
            )
        else:
            raise ValueError(f"暂不支持的操作类型：{action.action_type}")

        action.status = "executed"
        result_message = (
            "Calendar event created successfully."
            if action.action_type == "create_calendar_event"
            else "Gmail draft created successfully."
        )
        result_key = "calendar" if action.action_type == "create_calendar_event" else "gmail"
        action.result = json.dumps({"message": result_message, result_key: result_payload}, ensure_ascii=False)
        action.executed_at = datetime.now(timezone.utc)
        if action.draft_preview_id:
            preview = self.db.scalars(select(DraftPreview).where(DraftPreview.id == action.draft_preview_id)).first()
            if preview:
                preview.status = "created"
        if action.action_type == "create_calendar_event":
            suggestion_id = payload.get("suggestion_id")
            suggestion = self.db.scalars(
                select(CalendarSuggestion).where(CalendarSuggestion.id == suggestion_id)
            ).first()
            if suggestion:
                suggestion.status = "created"
        self.db.flush()
        return result_message

    def reject_action(self, action_id: str) -> None:
        user = self._current_user()
        action = self.db.scalars(
            select(PendingAction).where(PendingAction.id == action_id, PendingAction.user_id == user.id)
        ).first()
        if action is None:
            raise ValueError("待确认操作不存在。")
        if action.status != "pending":
            raise ValueError("该操作已经处理过。")
        action.status = "rejected"
        action.executed_at = datetime.now(timezone.utc)
        if action.draft_preview_id:
            preview = self.db.scalars(select(DraftPreview).where(DraftPreview.id == action.draft_preview_id)).first()
            if preview:
                preview.status = "rejected"
        self.db.flush()

    def _current_user(self) -> User:
        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user
