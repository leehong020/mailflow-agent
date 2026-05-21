"""第十二阶段主动写邮件 API 结构。"""

from pydantic import BaseModel, Field


class ComposeGenerateRequest(BaseModel):
    """主动写邮件生成请求。

    goal 是用户在右侧 AI 对话框输入的写信目标；其余字段来自左侧编辑器，
    用于支持“先手写一点，再让 AI 补全”的工作流。
    """

    goal: str = Field(min_length=1, max_length=2000)
    to: str = ""
    subject: str = ""
    body: str = ""
    tone: str = "polite"
    language: str = "auto"


class ComposeReviseRequest(BaseModel):
    """主动写邮件修改请求。"""

    instruction: str = Field(min_length=1, max_length=2000)
    to: str = ""
    subject: str = ""
    body: str = ""
    tone: str = "polite"
    language: str = "auto"


class ComposeDraftResponse(BaseModel):
    """主动写邮件统一响应。"""

    draft_preview_id: str
    to: str
    subject: str
    body: str
    tone: str
    language: str
    generation_reason: str
    trace_id: str | None = None
