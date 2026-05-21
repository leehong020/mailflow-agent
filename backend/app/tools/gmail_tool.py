"""Gmail API 工具层。

Tool 层只处理 Gmail API 的调用和响应解析，不保存数据，也不处理 HTTP 异常。
这样 Agent 工作流或普通 API 都可以复用同一套 Gmail 能力。
"""

import base64
from email.message import EmailMessage
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from googleapiclient.discovery import build


class GmailTool:
    """Gmail API 工具层，只负责把 Google 返回值转换成系统可用结构。"""

    def __init__(self, credentials) -> None:
        self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def list_recent_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """读取 Inbox 中最近的 Gmail message id，再逐封获取详情。"""

        response = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=limit)
            .execute()
        )
        messages = response.get("messages", [])
        return [self.get_message(message["id"]) for message in messages]

    def get_message(self, message_id: str) -> dict[str, Any]:
        """获取单封邮件详情，并整理成前端需要的字段。"""

        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = self._headers(raw.get("payload", {}).get("headers", []))
        body_text = self._extract_text(raw.get("payload", {}))
        label_ids = raw.get("labelIds", [])
        return {
            "id": raw["id"],
            "thread_id": raw.get("threadId"),
            "subject": headers.get("subject", "(无主题)"),
            "sender": headers.get("from", ""),
            "recipients": self._split_recipients(headers.get("to", "")),
            "label_ids": label_ids,
            "is_read": "UNREAD" not in label_ids,
            "is_starred": "STARRED" in label_ids,
            "mailbox_status": self._mailbox_status(label_ids),
            "received_at": self._received_at(raw, headers.get("date")),
            "snippet": raw.get("snippet", ""),
            "body_text": body_text,
            "body_preview": body_text[:500] if body_text else None,
        }

    def create_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """在 Gmail 中创建草稿。

        注意：这里只创建 draft，不发送邮件，符合 Human-in-the-loop 的安全要求。
        """

        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw_message}})
            .execute()
        )

    def send_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """发送 Gmail 邮件。

        该方法只由 Pending Actions 确认后调用，业务层不会直接暴露“立即发送”。
        """

        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

    def list_labels(self) -> list[dict[str, Any]]:
        """读取当前 Gmail 账号可用标签。

        label id 才是 Gmail API 修改标签时真正需要的值，前端展示时同时给出
        name，方便用户选择。
        """

        response = self.service.users().labels().list(userId="me").execute()
        return [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "type": item.get("type", ""),
            }
            for item in response.get("labels", [])
        ]

    def modify_message_labels(
        self,
        *,
        message_id: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """修改单封邮件的 Gmail labelIds。"""

        return (
            self.service.users()
            .messages()
            .modify(
                userId="me",
                id=message_id,
                body={
                    "addLabelIds": add_label_ids or [],
                    "removeLabelIds": remove_label_ids or [],
                },
            )
            .execute()
        )

    def trash_message(self, *, message_id: str) -> dict[str, Any]:
        """移动邮件到垃圾箱，不做永久删除。"""

        return self.service.users().messages().trash(userId="me", id=message_id).execute()

    def batch_modify_messages(
        self,
        *,
        message_ids: list[str],
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """批量修改邮件标签。

        Gmail batchModify 没有返回每封邮件详情，因此这里只返回本次请求摘要。
        """

        self.service.users().messages().batchModify(
            userId="me",
            body={
                "ids": message_ids,
                "addLabelIds": add_label_ids or [],
                "removeLabelIds": remove_label_ids or [],
            },
        ).execute()
        return {"message_ids": message_ids, "addLabelIds": add_label_ids or [], "removeLabelIds": remove_label_ids or []}

    @staticmethod
    def _headers(headers: list[dict[str, str]]) -> dict[str, str]:
        """把 Gmail header 列表转换成小写 key 的字典，方便取 subject/from/to。"""

        return {item["name"].lower(): item.get("value", "") for item in headers}

    def _extract_text(self, payload: dict[str, Any]) -> str:
        """递归解析 MIME 结构，优先返回 text/plain 内容。"""

        mime_type = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data")

        # Gmail 正文使用 base64url 编码；text/plain 是最适合列表预览的格式。
        if mime_type == "text/plain" and data:
            return self._decode_base64url(data)

        # 多段 MIME 邮件需要递归读取 parts。
        # 当前阶段优先拿纯文本，HTML 正文后续邮件详情页再增强。
        parts = payload.get("parts", [])
        plain_parts = [self._extract_text(part) for part in parts]
        return "\n".join(part for part in plain_parts if part).strip()

    @staticmethod
    def _decode_base64url(data: str) -> str:
        """解码 Gmail 使用的 base64url 正文。"""

        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode((data + padding).encode("utf-8"))
        return decoded.decode("utf-8", errors="replace")

    @staticmethod
    def _split_recipients(value: str) -> list[str]:
        """把 To header 拆成收件人列表。"""

        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _received_at(raw: dict[str, Any], header_date: str | None) -> str | None:
        """优先使用 Gmail internalDate 生成稳定的 ISO 时间。"""

        if raw.get("internalDate"):
            timestamp = int(raw["internalDate"]) / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        if not header_date:
            return None
        try:
            return parsedate_to_datetime(header_date).isoformat()
        except (TypeError, ValueError):
            return header_date

    @staticmethod
    def _mailbox_status(label_ids: list[str]) -> str:
        """根据系统标签推导本地邮箱状态。"""

        if "TRASH" in label_ids:
            return "trash"
        if "INBOX" not in label_ids:
            return "archived"
        return "inbox"
