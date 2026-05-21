"""大模型输出结构校验。

这些 schema 专门用于校验 Agent 调用大模型后返回的 JSON。
和接口响应 schema 不同，它们是“模型输出契约”：
1. 字段缺失、类型错误、枚举不合法时会抛出 ValidationError；
2. 可以安全修复的小问题会自动归一化，例如去空格、截断过长文本、
   把 priority 的大小写统一成小写；
3. 禁止模型返回提示词之外的多余字段，避免错误字段悄悄进入业务系统。
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PriorityValue = Literal["high", "medium", "low"]
CategoryValue = Literal[
    "urgent_reply",
    "normal_reply",
    "calendar_related",
    "task_required",
    "newsletter",
    "notification",
    "ignore",
]


def _clean_text(value: object, *, limit: int | None = None) -> str:
    """把模型返回值归一化成可展示字符串。"""

    text = str(value or "").strip()
    if limit is not None:
        text = text[:limit]
    return text


def _clean_text_list(value: object, *, limit: int, item_limit: int) -> list[str]:
    """把模型返回的列表字段整理成字符串列表。"""

    if value is None:
        return []
    if isinstance(value, str):
        # 模型偶尔会把数组写成换行文本，这种情况可以安全拆成列表。
        raw_items = [item.strip("-* \t") for item in value.splitlines()]
    elif isinstance(value, list):
        raw_items = value
    else:
        raise ValueError("字段必须是字符串数组。")

    items: list[str] = []
    for item in raw_items:
        text = _clean_text(item, limit=item_limit)
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _normalize_priority(value: object) -> str:
    """统一 priority 写法，并允许少量常见同义表达自动修复。"""

    text = _clean_text(value).lower()
    aliases = {
        "urgent": "high",
        "important": "high",
        "normal": "medium",
        "moderate": "medium",
        "minor": "low",
    }
    return aliases.get(text, text)


def _normalize_category(value: object) -> str:
    """统一 category 写法，并修复常见短名。"""

    text = _clean_text(value).lower()
    aliases = {
        "urgent": "urgent_reply",
        "reply": "normal_reply",
        "calendar": "calendar_related",
        "meeting": "calendar_related",
        "task": "task_required",
        "todo": "task_required",
        "notice": "notification",
        "skip": "ignore",
    }
    return aliases.get(text, text)


class LLMOutputBase(BaseModel):
    """模型输出基类。

    extra="forbid" 可以让多余字段立即暴露出来，而不是静默忽略。
    这对调试提示词和发现模型漂移很重要。
    """

    model_config = ConfigDict(extra="forbid")


class EmailSummaryLLMOutput(LLMOutputBase):
    """Email Summarizer Agent 的模型输出。"""

    summary: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("key_points", mode="before")
    @classmethod
    def normalize_key_points(cls, value: object) -> list[str]:
        return _clean_text_list(value, limit=5, item_limit=160)


class EmailTriageLLMOutput(LLMOutputBase):
    """Email Triage Agent 的模型输出。"""

    category: CategoryValue
    priority: PriorityValue
    need_reply: bool
    has_meeting_request: bool
    has_task: bool
    reason: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> str:
        return _normalize_category(value)

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> str:
        return _normalize_priority(value)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("recommended_actions", mode="before")
    @classmethod
    def normalize_actions(cls, value: object) -> list[str]:
        return _clean_text_list(value, limit=5, item_limit=120)


class ExtractedTaskLLMOutput(LLMOutputBase):
    """Task Extraction Agent 返回的单个任务。"""

    title: str = Field(min_length=1)
    description: str = ""
    deadline: str | None = None
    priority: PriorityValue

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> str:
        return _clean_text(value, limit=120)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: object) -> str:
        return _clean_text(value, limit=500)

    @field_validator("deadline", mode="before")
    @classmethod
    def normalize_deadline(cls, value: object) -> str | None:
        text = _clean_text(value, limit=80)
        return text or None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, value: object) -> str:
        return _normalize_priority(value)


class TaskExtractionLLMOutput(LLMOutputBase):
    """Task Extraction Agent 的模型输出。"""

    tasks: list[ExtractedTaskLLMOutput] = Field(default_factory=list, max_length=5)

    @field_validator("tasks", mode="before")
    @classmethod
    def normalize_tasks(cls, value: object) -> object:
        """任务列表过长时安全截断，非列表时交给 Pydantic 报错。"""

        if value is None:
            return []
        if isinstance(value, list):
            return value[:5]
        return value


class ReplyDraftLLMOutput(LLMOutputBase):
    """Reply Draft Agent 的模型输出。"""

    to: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    generation_reason: str = Field(min_length=1)

    @field_validator("to", mode="before")
    @classmethod
    def normalize_to(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("subject", mode="before")
    @classmethod
    def normalize_subject(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> str:
        return _clean_text(value, limit=5000)

    @field_validator("generation_reason", mode="before")
    @classmethod
    def normalize_generation_reason(cls, value: object) -> str:
        return _clean_text(value, limit=240)


class ComposeMailLLMOutput(LLMOutputBase):
    """Compose Mail Agent 的模型输出。

    主动写邮件时，用户可能一开始没有填写收件人，所以 to 允许为空；
    但 subject/body/reason 必须有内容，避免前端拿到一封无法编辑的空邮件。
    """

    to: str = ""
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    generation_reason: str = Field(min_length=1)

    @field_validator("to", mode="before")
    @classmethod
    def normalize_to(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("subject", mode="before")
    @classmethod
    def normalize_subject(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> str:
        return _clean_text(value, limit=5000)

    @field_validator("generation_reason", mode="before")
    @classmethod
    def normalize_generation_reason(cls, value: object) -> str:
        return _clean_text(value, limit=240)


class MemorySummaryLLMOutput(LLMOutputBase):
    """Memory Agent 的短期对话压缩输出。"""

    summary: str = Field(min_length=1)
    key_constraints: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("summary", mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> str:
        return _clean_text(value, limit=1000)

    @field_validator("key_constraints", mode="before")
    @classmethod
    def normalize_constraints(cls, value: object) -> list[str]:
        return _clean_text_list(value, limit=8, item_limit=160)


class CalendarSchedulerLLMOutput(LLMOutputBase):
    """Calendar Scheduler Agent 的模型输出。"""

    meeting_title: str = Field(min_length=1)
    participants: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(default=30, ge=15, le=240)
    time_window_start: str | None = None
    time_window_end: str | None = None
    timezone: str = "Asia/Shanghai"
    location: str = ""
    description: str = ""

    @field_validator("meeting_title", mode="before")
    @classmethod
    def normalize_meeting_title(cls, value: object) -> str:
        return _clean_text(value, limit=160)

    @field_validator("participants", mode="before")
    @classmethod
    def normalize_participants(cls, value: object) -> list[str]:
        return _clean_text_list(value, limit=12, item_limit=240)

    @field_validator("time_window_start", "time_window_end", mode="before")
    @classmethod
    def normalize_time_window(cls, value: object) -> str | None:
        text = _clean_text(value, limit=80)
        return text or None

    @field_validator("timezone", mode="before")
    @classmethod
    def normalize_timezone(cls, value: object) -> str:
        return _clean_text(value, limit=64) or "Asia/Shanghai"

    @field_validator("location", mode="before")
    @classmethod
    def normalize_location(cls, value: object) -> str:
        return _clean_text(value, limit=240)

    @field_validator("description", mode="before")
    @classmethod
    def normalize_calendar_description(cls, value: object) -> str:
        return _clean_text(value, limit=800)
