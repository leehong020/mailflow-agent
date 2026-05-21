"""第十三阶段写作记忆 API 结构。"""

from pydantic import BaseModel


class ComposeSessionInfo(BaseModel):
    id: str
    draft_preview_id: str = ""
    session_type: str
    title: str = ""
    editor_snapshot: dict = {}
    summary: str = ""
    created_at: str
    updated_at: str
    messages: list[dict] = []


class CreateComposeSessionRequest(BaseModel):
    draft_preview_id: str = ""
    session_type: str = "compose"
    title: str = ""
    editor_snapshot: dict = {}


class UpdateComposeSessionRequest(BaseModel):
    title: str | None = None
    editor_snapshot: dict | None = None


class ComposeMessageRequest(BaseModel):
    role: str
    content: str
    message_type: str = "normal"
    editor_snapshot: dict = {}


class ComposeMessageInfo(BaseModel):
    id: str
    role: str
    message_type: str = "normal"
    content: str
    editor_snapshot: dict = {}
    archived: bool = False
    created_at: str
