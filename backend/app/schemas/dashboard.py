"""Dashboard 首页统计响应结构。"""

from pydantic import BaseModel


class DashboardBreakdownItem(BaseModel):
    """Dashboard 分类统计项。"""

    label: str
    value: int


class DashboardRecentItem(BaseModel):
    """Dashboard 最近活动项。"""

    id: str
    title: str
    subtitle: str = ""
    status: str = ""
    created_at: str | None = None


class DashboardSummary(BaseModel):
    """工作台顶部统计卡片的数据。"""

    google_connected: bool
    email_count_today: int = 0
    analyzed_email_count: int = 0
    high_priority_count: int = 0
    need_reply_count: int = 0
    meeting_request_count: int = 0
    task_count: int = 0
    pending_action_count: int = 0
    today_event_count: int = 0
    calendar_suggestion_count: int = 0
    draft_preview_count: int = 0
    trace_count: int = 0
    category_breakdown: list[DashboardBreakdownItem] = []
    priority_breakdown: list[DashboardBreakdownItem] = []
    recent_emails: list[DashboardRecentItem] = []
    recent_actions: list[DashboardRecentItem] = []
    recent_traces: list[DashboardRecentItem] = []
