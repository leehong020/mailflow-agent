"""Human-in-the-loop 操作中心服务。

第七阶段把所有外部可见操作统一收敛到这里：
1. Safety Agent 评估风险；
2. 创建 PendingAction；
3. 用户确认后才调用 Gmail / Calendar 工具；
4. 用户拒绝时只更新本地状态，不触发外部 API。
"""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.safety_agent import SafetyAgent
from app.models.calendar import CalendarSuggestion
from app.models.draft import DraftPreview, PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService


class ActionService:
    """统一待确认操作服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.google_service = GoogleService(db)
        self.safety_agent = SafetyAgent()

    def create_action(
        self,
        *,
        action_type: str,
        payload: dict[str, Any],
        preview: dict[str, Any] | None = None,
        draft_preview_id: str | None = None,
    ) -> PendingAction:
        """创建一个待确认操作。

        调用方不直接指定风险等级，而是统一交给 SafetyAgent 判断。
        """

        user = self._current_user()
        decision = self.safety_agent.assess(action_type=action_type, payload=payload)
        preview_payload = dict(preview or payload)
        preview_payload["safety_reason"] = decision.reason

        action = PendingAction(
            user_id=user.id,
            action_type=action_type,
            draft_preview_id=draft_preview_id,
            payload=json.dumps(payload, ensure_ascii=False),
            preview=json.dumps(preview_payload, ensure_ascii=False),
            risk_level=decision.risk_level,
            status="pending" if decision.requires_confirmation else "approved",
        )
        self.db.add(action)
        self.db.flush()
        return action

    def list_actions(
        self,
        *,
        status: str | None = "pending",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PendingAction], int]:
        """分页查询待确认操作。"""

        user = self._current_user()
        query = select(PendingAction).where(PendingAction.user_id == user.id).order_by(PendingAction.created_at.desc())
        # status=all 用于前端查看历史操作；None 或空字符串也表示不过滤。
        if status and status != "all":
            query = query.where(PendingAction.status == status)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.offset(offset).limit(limit)).all()
        return list(items), total

    def confirm_action(self, action_id: str) -> str:
        """用户确认后执行外部操作。"""

        user = self._current_user()
        action = self._get_action_for_user(action_id=action_id, user=user)
        if action.status != "pending":
            raise ValueError("该操作已经处理过。")

        payload = json.loads(action.payload or "{}")
        try:
            result_message, result_key, result_payload = self._execute_action(action_type=action.action_type, payload=payload)
        except Exception as exc:
            action.status = "failed"
            action.result = json.dumps({"message": str(exc)}, ensure_ascii=False)
            action.executed_at = datetime.now(timezone.utc)
            self.db.flush()
            raise

        action.status = "executed"
        action.result = json.dumps({"message": result_message, result_key: result_payload}, ensure_ascii=False)
        action.executed_at = datetime.now(timezone.utc)
        self._mark_related_resource(action=action, payload=payload, status="created")
        self.db.flush()
        return result_message

    def reject_action(self, action_id: str) -> None:
        """用户拒绝操作，只更新本地状态。"""

        user = self._current_user()
        action = self._get_action_for_user(action_id=action_id, user=user)
        if action.status != "pending":
            raise ValueError("该操作已经处理过。")
        action.status = "rejected"
        action.executed_at = datetime.now(timezone.utc)
        self._mark_related_resource(action=action, payload=json.loads(action.payload or "{}"), status="rejected")
        self.db.flush()

    def _execute_action(self, *, action_type: str, payload: dict[str, Any]) -> tuple[str, str, dict]:
        """根据 action_type 调用真实外部工具。"""

        if action_type == "create_gmail_draft":
            result = self.google_service.create_gmail_draft(
                to=str(payload.get("to") or ""),
                subject=str(payload.get("subject") or ""),
                body=str(payload.get("body") or ""),
            )
            return "Gmail draft created successfully.", "gmail", result
        if action_type == "send_email":
            result = self.google_service.send_gmail_message(
                to=str(payload.get("to") or ""),
                subject=str(payload.get("subject") or ""),
                body=str(payload.get("body") or ""),
            )
            return "Gmail email sent successfully.", "gmail", result
        if action_type == "create_calendar_event":
            result = self.google_service.create_calendar_event(
                summary=str(payload.get("summary") or ""),
                start=str(payload.get("start") or ""),
                end=str(payload.get("end") or ""),
                attendees=list(payload.get("attendees") or []),
                description=str(payload.get("description") or ""),
                location=str(payload.get("location") or ""),
                timezone=str(payload.get("timezone") or "Asia/Shanghai"),
            )
            return "Calendar event created successfully.", "calendar", result
        if action_type == "modify_calendar_event":
            result = self.google_service.update_calendar_event(
                event_id=str(payload.get("event_id") or ""),
                summary=str(payload.get("summary") or ""),
                start=str(payload.get("start") or ""),
                end=str(payload.get("end") or ""),
                attendees=list(payload.get("attendees") or []),
                description=str(payload.get("description") or ""),
                location=str(payload.get("location") or ""),
                timezone=str(payload.get("timezone") or "Asia/Shanghai"),
            )
            return "Calendar event updated successfully.", "calendar", result
        if action_type == "delete_calendar_event":
            result = self.google_service.delete_calendar_event(event_id=str(payload.get("event_id") or ""))
            return "Calendar event deleted successfully.", "calendar", result
        if action_type == "archive_email":
            gmail_message_ids = list(payload.get("gmail_message_ids") or [])
            result = self.google_service.modify_gmail_message(
                gmail_message_id=str(gmail_message_ids[0]),
                add_label_ids=list(payload.get("add_label_ids") or []),
                remove_label_ids=list(payload.get("remove_label_ids") or ["INBOX"]),
            )
            self._apply_email_label_delta(payload=payload, add_label_ids=[], remove_label_ids=["INBOX"])
            return "Email archived successfully.", "gmail", result
        if action_type == "trash_email":
            gmail_message_ids = list(payload.get("gmail_message_ids") or [])
            result = self.google_service.trash_gmail_message(
                gmail_message_id=str(gmail_message_ids[0])
            )
            self._apply_email_label_delta(payload=payload, add_label_ids=["TRASH"], remove_label_ids=["INBOX"])
            return "Email moved to trash successfully.", "gmail", result
        if action_type == "modify_email_labels":
            add_labels = list(payload.get("add_label_ids") or [])
            remove_labels = list(payload.get("remove_label_ids") or [])
            gmail_message_ids = list(payload.get("gmail_message_ids") or [])
            result = self.google_service.modify_gmail_message(
                gmail_message_id=str(gmail_message_ids[0]),
                add_label_ids=add_labels,
                remove_label_ids=remove_labels,
            )
            self._apply_email_label_delta(payload=payload, add_label_ids=add_labels, remove_label_ids=remove_labels)
            return "Email labels updated successfully.", "gmail", result
        if action_type == "batch_email_operation":
            operation = str(payload.get("operation") or "")
            gmail_message_ids = list(payload.get("gmail_message_ids") or [])
            add_labels = list(payload.get("add_label_ids") or [])
            remove_labels = list(payload.get("remove_label_ids") or [])
            if operation == "trash":
                result = {
                    "items": [
                        self.google_service.trash_gmail_message(gmail_message_id=str(message_id))
                        for message_id in gmail_message_ids
                    ]
                }
            else:
                result = self.google_service.batch_modify_gmail_messages(
                    gmail_message_ids=[str(message_id) for message_id in gmail_message_ids],
                    add_label_ids=add_labels,
                    remove_label_ids=remove_labels,
                )
            self._apply_email_label_delta(payload=payload, add_label_ids=add_labels, remove_label_ids=remove_labels)
            return "Batch email operation executed successfully.", "gmail", result
        raise ValueError(f"暂不支持的操作类型：{action_type}")

    def _mark_related_resource(self, *, action: PendingAction, payload: dict[str, Any], status: str) -> None:
        """同步更新草稿预览或日程建议状态。"""

        if action.draft_preview_id:
            preview = self.db.scalars(select(DraftPreview).where(DraftPreview.id == action.draft_preview_id)).first()
            if preview:
                preview.status = "sent" if action.action_type == "send_email" and status == "created" else status
        if action.action_type == "create_calendar_event":
            suggestion = self.db.scalars(
                select(CalendarSuggestion).where(CalendarSuggestion.id == payload.get("suggestion_id"))
            ).first()
            if suggestion:
                suggestion.status = status

    def _apply_email_label_delta(
        self,
        *,
        payload: dict[str, Any],
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> None:
        """外部 Gmail 操作成功后同步本地邮件状态。"""

        email_ids = list(payload.get("email_ids") or [])
        if not email_ids:
            return
        emails = self.db.scalars(select(EmailRecord).where(EmailRecord.id.in_(email_ids))).all()
        for email in emails:
            labels = set(email.label_ids or [])
            labels.update(add_label_ids)
            labels.difference_update(remove_label_ids)
            email.label_ids = sorted(labels)
            email.is_read = "UNREAD" not in labels
            email.is_starred = "STARRED" in labels
            if "TRASH" in labels:
                email.mailbox_status = "trash"
            elif "INBOX" not in labels:
                email.mailbox_status = "archived"
            else:
                email.mailbox_status = "inbox"

    def _get_action_for_user(self, *, action_id: str, user: User) -> PendingAction:
        """按当前用户查询操作，防止跨用户确认。"""

        action = self.db.scalars(
            select(PendingAction).where(PendingAction.id == action_id, PendingAction.user_id == user.id)
        ).first()
        if action is None:
            raise ValueError("待确认操作不存在。")
        return action

    def _current_user(self) -> User:
        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user
