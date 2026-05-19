"""第六阶段日程 API 结构。"""

from pydantic import BaseModel, Field


class CalendarEventInfo(BaseModel):
    """前端日历视图展示的 Google Calendar 事件。"""

    id: str
    summary: str
    start: str
    end: str
    location: str = ""
    description: str = ""
    html_link: str = ""
    attendees: list[str] = []


class CalendarEventsResponse(BaseModel):
    items: list[CalendarEventInfo]
    total: int


class CalendarSlotInfo(BaseModel):
    """推荐的可用时间段。"""

    start: str
    end: str
    reason: str


class SuggestSlotsRequest(BaseModel):
    """从会议邮件生成日程建议的请求。"""

    email_id: str
    duration_minutes: int = Field(default=30, ge=15, le=240)


class CalendarSuggestionInfo(BaseModel):
    """日程建议详情。"""

    id: str
    source_email_id: str
    meeting_title: str
    description: str = ""
    location: str = ""
    timezone: str = "Asia/Shanghai"
    duration_minutes: int
    participants: list[str]
    suggested_slots: list[CalendarSlotInfo]
    selected_slot: CalendarSlotInfo | None = None
    status: str
    created_at: str | None = None


class SuggestSlotsResponse(BaseModel):
    suggestion: CalendarSuggestionInfo


class CreateCalendarPendingActionRequest(BaseModel):
    """用户选择时间段后创建待确认日程操作。"""

    selected_slot: CalendarSlotInfo


class CreateCalendarPendingActionResponse(BaseModel):
    action_id: str
    status: str
    message: str
