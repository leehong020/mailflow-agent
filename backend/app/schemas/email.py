"""邮件接口响应结构。"""

from pydantic import BaseModel


class EmailListItem(BaseModel):
    """Inbox 列表中的单封邮件摘要。"""

    id: str
    thread_id: str | None = None
    subject: str
    sender: str
    recipients: list[str] = []
    received_at: str | None = None
    snippet: str
    body_preview: str | None = None


class EmailListResponse(BaseModel):
    """邮件列表统一响应，保留 total 方便后续做分页。"""

    items: list[EmailListItem]
    total: int
