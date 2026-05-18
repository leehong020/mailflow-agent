"""Dashboard 首页统计响应结构。"""

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """工作台顶部统计卡片的数据。"""

    google_connected: bool
    email_count_today: int = 0
    high_priority_count: int = 0
    need_reply_count: int = 0
    meeting_request_count: int = 0
    pending_action_count: int = 0
    today_event_count: int = 0
