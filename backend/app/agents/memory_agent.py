"""Memory Agent。

该 Agent 只负责需要大模型理解能力的“短期对话摘要压缩”。
数据库读写、归档旧消息、恢复会话等确定性操作仍由 MemoryService 完成。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.schemas.llm_outputs import MemorySummaryLLMOutput


@dataclass(frozen=True)
class MemorySummaryResult:
    """MemoryAgent 的摘要输出。"""

    summary: str
    key_constraints: list[str]


class MemoryAgent(BaseLLMAgent):
    """短期会话摘要 Agent。"""

    name = "MemoryAgent"
    prompt_file = "memory_agent.txt"

    def summarize(self, *, existing_summary: str, messages: list[dict], editor_snapshot: dict) -> MemorySummaryResult:
        """总结较早的对话消息，避免后续模型上下文过长。"""

        try:
            return self._summarize_with_llm(
                existing_summary=existing_summary,
                messages=messages,
                editor_snapshot=editor_snapshot,
            )
        except Exception as exc:
            return self._fallback(existing_summary=existing_summary, messages=messages, error=exc)

    def _summarize_with_llm(
        self,
        *,
        existing_summary: str,
        messages: list[dict],
        editor_snapshot: dict,
    ) -> MemorySummaryResult:
        """调用大模型生成结构化短期记忆摘要。"""

        message_text = "\n".join(
            f"{item.get('role', '')}: {item.get('content', '')}" for item in messages
        )
        data = self.run_json(
            user_prompt=(
                "请压缩下面这段草稿工作台对话，只保留对后续写作仍然重要的信息。\n\n"
                f"已有摘要：{existing_summary or '无'}\n\n"
                f"当前编辑器快照：{editor_snapshot}\n\n"
                f"待压缩对话：\n{message_text}"
            )
        )
        output = self.validate_llm_output(MemorySummaryLLMOutput, data)
        return MemorySummaryResult(summary=output.summary, key_constraints=output.key_constraints)

    @staticmethod
    def _fallback(*, existing_summary: str, messages: list[dict], error: Exception | None) -> MemorySummaryResult:
        """模型不可用时的保守摘要，至少不阻断用户写作。"""

        recent = "；".join(str(item.get("content", "")).strip() for item in messages[-6:] if item.get("content"))
        summary = existing_summary.strip()
        if recent:
            summary = f"{summary}；近期对话要点：{recent}" if summary else f"近期对话要点：{recent}"
        if error:
            summary = f"{summary}（自动摘要模型不可用，已使用保守摘要：{BaseLLMAgent.error_summary(error, limit=100)}）"
        return MemorySummaryResult(summary=summary[:1000], key_constraints=[])
