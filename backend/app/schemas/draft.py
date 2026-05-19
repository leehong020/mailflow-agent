"""第五阶段草稿与待确认操作的 API 结构。"""

from pydantic import BaseModel


class DraftPreviewInfo(BaseModel):
    id: str
    source_email_id: str
    to: str
    subject: str
    body: str
    tone: str = "polite"
    language: str = "en"
    status: str = "preview"
    generation_reason: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class DraftPreviewListResponse(BaseModel):
    items: list[DraftPreviewInfo]
    total: int


class CreateDraftPreviewRequest(BaseModel):
    tone: str = "polite"
    language: str = "en"


class CreateDraftPreviewResponse(BaseModel):
    draft_preview_id: str
    to: str
    subject: str
    body: str
    requires_confirmation: bool = True
    generation_reason: str = ""


class UpdateDraftPreviewRequest(BaseModel):
    tone: str = "polite"
    language: str = "en"
    body: str | None = None
    subject: str | None = None


class UpdateDraftPreviewResponse(BaseModel):
    draft_preview_id: str
    to: str
    subject: str
    body: str
    tone: str
    language: str
    generation_reason: str = ""


class CreatePendingActionForDraftResponse(BaseModel):
    action_id: str
    status: str
    message: str


class PendingActionInfo(BaseModel):
    id: str
    action_type: str
    draft_preview_id: str | None = None
    payload: dict
    preview: dict
    risk_level: str = "medium"
    status: str = "pending"
    result: dict | None = None
    created_at: str
    executed_at: str | None = None


class PendingActionListResponse(BaseModel):
    items: list[PendingActionInfo]
    total: int


class ConfirmActionResponse(BaseModel):
    status: str
    result: str


class RejectActionResponse(BaseModel):
    status: str
    message: str
