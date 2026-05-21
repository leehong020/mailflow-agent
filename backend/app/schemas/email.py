"""邮件接口响应结构。"""

from pydantic import BaseModel, Field


class EmailAnalysisInfo(BaseModel):
    """邮件分析结果。"""

    summary: str = ""
    key_points: list[str] = []
    category: str = "notification"
    priority: str = "low"
    need_reply: bool = False
    has_task: bool = False
    has_meeting_request: bool = False
    reason: str = ""
    recommended_actions: list[str] = []


class TaskInfo(BaseModel):
    """邮件中提取出的待办事项。"""

    id: str
    title: str
    description: str = ""
    deadline: str | None = None
    priority: str = "medium"
    status: str = "todo"


class EmailListItem(BaseModel):
    """Inbox 列表中的单封邮件摘要。"""

    id: str
    thread_id: str | None = None
    subject: str
    sender: str
    recipients: list[str] = []
    label_ids: list[str] = []
    is_read: bool = True
    is_starred: bool = False
    mailbox_status: str = "inbox"
    received_at: str | None = None
    snippet: str
    body_preview: str | None = None
    analysis: EmailAnalysisInfo | None = None


class EmailListResponse(BaseModel):
    """邮件列表统一响应，保留 total 方便后续做分页。"""

    items: list[EmailListItem]
    total: int
    analyzed_total: int = 0
    unanalyzed_total: int = 0


class EmailDetailResponse(EmailListItem):
    """邮件详情页响应。"""

    body_text: str = ""
    tasks: list[TaskInfo] = []


class AnalyzeEmailsRequest(BaseModel):
    """触发邮件分析请求。"""

    range: str = "recent"
    limit: int = 20


class AnalyzeEmailsResponse(BaseModel):
    """触发邮件分析响应。"""

    status: str
    analyzed_count: int
    message: str
    trace_ids: list[str] = []


class SyncEmailsResponse(BaseModel):
    """同步 Gmail 响应。"""

    status: str
    synced_count: int
    message: str


class SyncEmailsRequest(BaseModel):
    """同步 Gmail 最近邮件的请求参数。

    该请求只负责把 Gmail 最新邮件保存/更新到本地数据库，不会触发大模型分析。
    给 limit 设置上限，可以避免刷新看板时一次拉取过多邮件导致接口响应变慢。
    """

    limit: int = Field(default=20, ge=1, le=50)


class ReanalyzeEmailResponse(BaseModel):
    """单封邮件重新分析响应。"""

    status: str
    message: str


class GmailLabelInfo(BaseModel):
    """Gmail 标签信息。"""

    id: str
    name: str
    type: str = ""


class GmailLabelListResponse(BaseModel):
    """Gmail 标签列表响应。"""

    items: list[GmailLabelInfo]


class EmailOperationResponse(BaseModel):
    """单封邮件操作响应。"""

    status: str
    message: str
    action_id: str | None = None
    email: EmailListItem | None = None


class LabelActionRequest(BaseModel):
    """修改标签请求。"""

    add_label_ids: list[str] = []
    remove_label_ids: list[str] = []


class BatchEmailActionRequest(BaseModel):
    """批量邮件操作请求。"""

    email_ids: list[str]
    operation: str
    add_label_ids: list[str] = []
    remove_label_ids: list[str] = []
