"""第九阶段 Gmail 邮件管理操作服务。

该服务专门处理 Gmail 管理动作：
1. 低风险动作直接执行，例如标记已读 / 未读、星标 / 取消星标；
2. 高风险动作创建 PendingAction，例如归档、移动垃圾箱、修改标签、批量操作；
3. 外部 API 成功后同步更新本地 EmailRecord，保证 Inbox 和详情页状态一致。
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draft import PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.action_service import ActionService
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService


class EmailOperationService:
    """Gmail 邮件管理服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.google_service = GoogleService(db)
        self.action_service = ActionService(db)

    def list_labels(self) -> list[dict[str, str]]:
        """读取 Gmail 标签列表。"""

        return self.google_service.list_gmail_labels()

    def execute_quick_operation(self, *, email_id: str, operation: str) -> EmailRecord:
        """执行低风险单封邮件操作。

        mark_read / mark_unread / star / unstar 只改变显示状态，不会删除或隐藏邮件，
        因此可以直接执行；执行后立即同步本地字段。
        """

        email = self._get_email(email_id)
        add_labels, remove_labels = self._labels_for_operation(operation)
        self.google_service.modify_gmail_message(
            gmail_message_id=email.gmail_message_id,
            add_label_ids=add_labels,
            remove_label_ids=remove_labels,
        )
        self._apply_label_delta(email=email, add_label_ids=add_labels, remove_label_ids=remove_labels)
        self.db.flush()
        return email

    def create_archive_action(self, *, email_id: str) -> PendingAction:
        """创建归档待确认操作。"""

        email = self._get_email(email_id)
        return self._create_action(
            action_type="archive_email",
            emails=[email],
            payload_extra={"add_label_ids": [], "remove_label_ids": ["INBOX"]},
            preview_extra={"操作": "归档邮件"},
        )

    def create_trash_action(self, *, email_id: str) -> PendingAction:
        """创建移动到垃圾箱待确认操作。"""

        email = self._get_email(email_id)
        return self._create_action(
            action_type="trash_email",
            emails=[email],
            payload_extra={},
            preview_extra={"操作": "移动到垃圾箱"},
        )

    def create_labels_action(
        self,
        *,
        email_id: str,
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> PendingAction:
        """创建修改标签待确认操作。"""

        email = self._get_email(email_id)
        return self._create_action(
            action_type="modify_email_labels",
            emails=[email],
            payload_extra={"add_label_ids": add_label_ids, "remove_label_ids": remove_label_ids},
            preview_extra={"操作": "修改邮件标签", "添加标签": add_label_ids, "移除标签": remove_label_ids},
        )

    def create_batch_action(
        self,
        *,
        email_ids: list[str],
        operation: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> PendingAction:
        """创建批量邮件待确认操作。"""

        emails = self._get_emails(email_ids)
        if not emails:
            raise ValueError("请选择至少一封邮件。")

        add_labels, remove_labels = self._batch_label_delta(
            operation=operation,
            add_label_ids=add_label_ids or [],
            remove_label_ids=remove_label_ids or [],
        )
        return self._create_action(
            action_type="batch_email_operation",
            emails=emails,
            payload_extra={
                "operation": operation,
                "add_label_ids": add_labels,
                "remove_label_ids": remove_labels,
            },
            preview_extra={"操作": f"批量 {operation}", "邮件数量": len(emails)},
        )

    def _create_action(
        self,
        *,
        action_type: str,
        emails: list[EmailRecord],
        payload_extra: dict[str, Any],
        preview_extra: dict[str, Any],
    ) -> PendingAction:
        """创建邮件管理 PendingAction。"""

        payload = {
            "email_ids": [email.id for email in emails],
            "gmail_message_ids": [email.gmail_message_id for email in emails],
            **payload_extra,
        }
        preview = {
            "邮件主题": [email.subject for email in emails[:5]],
            "影响邮件数": len(emails),
            **preview_extra,
        }
        return self.action_service.create_action(action_type=action_type, payload=payload, preview=preview)

    def _get_email(self, email_id: str) -> EmailRecord:
        """按当前用户读取单封邮件。"""

        user = self._current_user()
        email = self.db.scalars(
            select(EmailRecord).where(EmailRecord.id == email_id, EmailRecord.user_id == user.id)
        ).first()
        if email is None:
            raise ValueError("邮件不存在。")
        return email

    def _get_emails(self, email_ids: list[str]) -> list[EmailRecord]:
        """按当前用户读取多封邮件，防止跨用户批量操作。"""

        user = self._current_user()
        return list(
            self.db.scalars(
                select(EmailRecord).where(EmailRecord.user_id == user.id, EmailRecord.id.in_(email_ids))
            ).all()
        )

    @staticmethod
    def _labels_for_operation(operation: str) -> tuple[list[str], list[str]]:
        """把低风险操作映射成 Gmail label 增删。"""

        mapping = {
            "mark_read": ([], ["UNREAD"]),
            "mark_unread": (["UNREAD"], []),
            "star": (["STARRED"], []),
            "unstar": ([], ["STARRED"]),
        }
        if operation not in mapping:
            raise ValueError(f"不支持的快速操作：{operation}")
        return mapping[operation]

    @staticmethod
    def _batch_label_delta(
        *,
        operation: str,
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> tuple[list[str], list[str]]:
        """把批量操作映射成 Gmail batchModify 参数。"""

        mapping = {
            "mark_read": ([], ["UNREAD"]),
            "mark_unread": (["UNREAD"], []),
            "star": (["STARRED"], []),
            "unstar": ([], ["STARRED"]),
            "archive": ([], ["INBOX"]),
            "trash": (["TRASH"], ["INBOX"]),
            "labels": (add_label_ids, remove_label_ids),
        }
        if operation not in mapping:
            raise ValueError(f"不支持的批量操作：{operation}")
        return mapping[operation]

    @staticmethod
    def _apply_label_delta(
        *,
        email: EmailRecord,
        add_label_ids: list[str],
        remove_label_ids: list[str],
    ) -> None:
        """把 Gmail label 变化同步到本地状态。"""

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

    def _current_user(self) -> User:
        """获取当前演示用户。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user
