"""邮件接口响应结构。"""

from pydantic import BaseModel


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
    received_at: str | None = None
    snippet: str
    body_preview: str | None = None
    analysis: EmailAnalysisInfo | None = None


class EmailListResponse(BaseModel):
    """邮件列表统一响应，保留 total 方便后续做分页。"""

    items: list[EmailListItem]
    total: int


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


class ReanalyzeEmailResponse(BaseModel):
    """单封邮件重新分析响应。"""

    status: str
    message: str
