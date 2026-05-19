"""统一大模型客户端。

本项目使用 DashScope 的 OpenAI-compatible 接口，因此可以直接使用
openai Python SDK 的 chat.completions.create。

Agent 层只调用 complete_json，不直接关心供应商、base_url、api_key。
这样后续切换 OpenAI、DeepSeek、Qwen 或其他兼容服务时，只需要修改 .env。
"""

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


class LLMClient:
    """OpenAI-compatible 大模型客户端。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.llm_api_key:
            raise RuntimeError("未配置 LLM_API_KEY，无法调用大模型 Agent。")

        # OpenAI SDK 支持自定义 base_url。
        # DashScope compatible mode 的 base_url 配在 backend/.env 中。
        self.client = OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
        )

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """调用模型并解析 JSON 对象。

        prompt 中会强约束模型只返回 JSON；这里仍做容错解析，避免模型在 JSON 外
        包一层说明文字时导致整个 Agent 失败。
        """

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        return self._loads_json_object(content)

    @staticmethod
    def _loads_json_object(content: str) -> dict[str, Any]:
        """解析模型返回的 JSON 对象。"""

        text = content.strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < start:
                raise
            value = json.loads(text[start : end + 1])

        if not isinstance(value, dict):
            raise ValueError("模型返回值不是 JSON object。")
        return value
