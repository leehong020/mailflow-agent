"""Email Summarizer Agent。

职责来自开发文档第 9.5 节：
- 生成邮件摘要；
- 提取关键点；
- 为前端详情页提供结构化分析结果。

当前实现优先调用大模型生成结构化 JSON。
如果模型不可用，则使用本地规则兜底，保证演示流程不中断。
"""

from dataclasses import dataclass

from app.core.llm import LLMClient
from app.models.email import EmailRecord
from app.prompts import EMAIL_SUMMARIZER_SYSTEM_PROMPT


@dataclass(frozen=True)
class EmailSummaryResult:
    """摘要 Agent 的结构化输出。"""

    summary: str
    key_points: list[str]


class EmailSummarizerAgent:
    """邮件摘要 Agent。"""

    name = "EmailSummarizerAgent"
    system_prompt = EMAIL_SUMMARIZER_SYSTEM_PROMPT

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def summarize(self, email: EmailRecord) -> EmailSummaryResult:
        """根据邮件正文生成短摘要和关键点。"""

        content = self._normalize(email.body_text or email.snippet or email.subject)
        if not content:
            return EmailSummaryResult(summary="该邮件暂无可分析的正文内容。", key_points=[])

        try:
            return self._summarize_with_llm(email=email, content=content)
        except Exception:
            # 大模型异常时降级规则摘要，避免单封邮件分析失败影响整体流程。
            return self._summarize_with_rules(content)

    def _summarize_with_llm(self, *, email: EmailRecord, content: str) -> EmailSummaryResult:
        """调用大模型生成摘要。"""

        client = self.llm_client or LLMClient()
        data = client.complete_json(
            system_prompt=self.system_prompt,
            user_prompt=(
                f"邮件主题：{email.subject}\n"
                f"发件人：{email.sender}\n"
                f"邮件正文：\n{content[:6000]}\n\n"
                "请输出摘要和关键点。"
            ),
        )
        summary = str(data.get("summary") or "").strip()[:240]
        key_points = data.get("key_points") or []
        if not isinstance(key_points, list):
            key_points = []
        key_points = [str(item).strip() for item in key_points if str(item).strip()][:5]
        return EmailSummaryResult(summary=summary or content[:160], key_points=key_points)

    def _summarize_with_rules(self, content: str) -> EmailSummaryResult:
        """规则兜底摘要。"""

        summary = content[:160] + ("..." if len(content) > 160 else "")
        key_points = self._extract_key_points(content)
        return EmailSummaryResult(summary=summary, key_points=key_points)

    @staticmethod
    def _normalize(value: str) -> str:
        """压缩多余空白，提升摘要和关键点展示质量。"""

        return " ".join(value.replace("\r", "\n").split())

    @staticmethod
    def _extract_key_points(content: str) -> list[str]:
        """从正文中提取最多 4 个关键句。"""

        separators = ["。", "！", "？", ".", "!", "?"]
        sentences = [content]
        for separator in separators:
            next_sentences: list[str] = []
            for sentence in sentences:
                next_sentences.extend(sentence.split(separator))
            sentences = next_sentences

        key_points = [item.strip() for item in sentences if len(item.strip()) >= 8]
        return key_points[:4]
