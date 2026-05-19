"""大模型 Agent 的通用基类。

这里把所有 Agent 共同需要的能力集中起来：
1. 从 prompts 目录读取独立的 txt 系统提示词；
2. 调用 OpenAI-compatible 大模型客户端；
3. 组装统一的邮件上下文；
4. 对模型输出做轻量清洗和边界保护。

这样每个具体 Agent 只需要关注自己的业务职责，代码会更像“模型驱动的
Agent 节点”，而不是散落在各处的关键词规则。
"""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.llm import LLMClient
from app.models.email import EmailRecord
from app.prompts import load_prompt


LLMOutputT = TypeVar("LLMOutputT", bound=BaseModel)


class BaseLLMAgent:
    """所有大模型 Agent 的基础能力。

    子类通过 prompt_file 指定自己的系统提示词文件，例如
    email_triage_agent.txt。业务方法里调用 run_json 即可获得模型返回的
    JSON object。
    """

    name = "BaseLLMAgent"
    prompt_file = ""
    max_email_chars = 8000

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        # 允许测试时传入假的 LLMClient；生产环境默认从 .env 读取模型配置。
        self.llm_client = llm_client

    @property
    def system_prompt(self) -> str:
        """读取当前 Agent 的系统提示词。"""

        return load_prompt(self.prompt_file)

    def run_json(self, user_prompt: str) -> dict:
        """调用大模型并要求返回 JSON object。"""

        client = self.llm_client or LLMClient()
        return client.complete_json(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
        )

    def validate_llm_output(self, schema: type[LLMOutputT], data: dict) -> LLMOutputT:
        """使用 Pydantic 校验模型输出。

        校验失败时抛出带 Agent 名称的 ValueError。上层 Agent 可以选择把错误
        记录到 Trace，或进入 fallback 兜底逻辑。
        """

        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"{self.name} 的 LLM 输出不符合 schema：{exc}") from exc

    @staticmethod
    def error_summary(error: Exception | None, *, limit: int = 160) -> str:
        """把异常压缩成适合前端展示和数据库保存的一行文本。"""

        if error is None:
            return "未知错误"
        text = " ".join(str(error).split())
        return text[:limit]

    def build_email_context(self, email: EmailRecord) -> str:
        """把邮件对象整理成模型容易理解的上下文。

        上下文中尽量保留发件人、收件人、时间、主题、摘要和正文。这里不做
        关键词判断，只负责把业务事实交给模型。
        """

        recipients = ", ".join(email.recipients or [])
        received_at = email.received_at.isoformat() if email.received_at else ""
        body = self.compact_text(email.body_text or email.snippet or "")
        body = self.truncate(body, self.max_email_chars)
        return (
            f"邮件ID：{email.id}\n"
            f"Gmail Message ID：{email.gmail_message_id}\n"
            f"主题：{email.subject or '(无主题)'}\n"
            f"发件人：{email.sender or ''}\n"
            f"收件人：{recipients}\n"
            f"接收时间：{received_at}\n"
            f"Snippet：{email.snippet or ''}\n"
            f"正文：\n{body}"
        )

    @staticmethod
    def compact_text(value: str | None) -> str:
        """压缩多余空白，避免把无意义换行浪费给模型。"""

        if not value:
            return ""
        return " ".join(value.replace("\r", "\n").split())

    @staticmethod
    def truncate(value: str, limit: int) -> str:
        """限制发给模型的上下文长度，避免单封长邮件拖垮调用。"""

        if len(value) <= limit:
            return value
        return value[:limit] + "\n[内容过长，已截断]"

    @staticmethod
    def clean_text(value: object, *, default: str = "", limit: int | None = None) -> str:
        """把模型返回值清洗成可保存、可展示的字符串。"""

        text = str(value or default).strip()
        if limit is not None:
            text = text[:limit]
        return text

    @staticmethod
    def clean_string_list(value: object, *, limit: int, item_limit: int = 160) -> list[str]:
        """把模型返回的列表字段清洗成字符串数组。"""

        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                items.append(text[:item_limit])
            if len(items) >= limit:
                break
        return items

    @staticmethod
    def choose(value: object, allowed: set[str], default: str) -> str:
        """把模型枚举输出约束在系统允许的范围内。"""

        text = str(value or "").strip()
        return text if text in allowed else default
