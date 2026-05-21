"""Human-in-the-loop 待确认操作 API 结构。"""

from pydantic import BaseModel


class ActionInfo(BaseModel):
    """Pending Actions 页面展示的单个操作。"""

    id: str
    action_type: str
    draft_preview_id: str | None = None
    payload: dict
    preview: dict
    risk_level: str
    status: str
    result: dict | None = None
    created_at: str
    executed_at: str | None = None


class ActionListResponse(BaseModel):
    items: list[ActionInfo]
    total: int


class ConfirmActionResponse(BaseModel):
    status: str
    result: str


class RejectActionResponse(BaseModel):
    status: str
    message: str
