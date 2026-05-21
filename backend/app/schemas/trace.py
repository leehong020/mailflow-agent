"""Agent 执行轨迹接口结构。"""

from pydantic import BaseModel


class TraceEventInfo(BaseModel):
    """单步轨迹事件。"""

    id: str
    step: int
    agent_name: str
    status: str
    message: str
    input_preview: str = ""
    output_preview: str = ""
    created_at: str


class TraceInfo(BaseModel):
    """单次轨迹总览。"""

    id: str
    task_type: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    created_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    events: list[TraceEventInfo] = []


class TraceListItem(BaseModel):
    """轨迹列表项，用于前端时间线概览。"""

    id: str
    task_type: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    created_at: str
    duration_ms: int | None = None


class TraceListResponse(BaseModel):
    """轨迹列表响应。"""

    items: list[TraceListItem]
    total: int
