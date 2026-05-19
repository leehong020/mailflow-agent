"""Email Summarizer Agent。

该 Agent 是开发文档第三阶段的邮件摘要节点。现在的主路径是：
1. 读取独立 txt 系统提示词；
2. 把邮件整理为完整上下文；
3. 调用大模型生成结构化 JSON；
4. 对 JSON 字段做轻量校验后返回给工作流。

只有在模型不可用时才使用本地兜底摘要，避免演示流程中断。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.models.email import EmailRecord
from app.schemas.llm_outputs import EmailSummaryLLMOutput


@dataclass(frozen=True)
class EmailSummaryResult:
    """摘要 Agent 的结构化输出。"""

    summary: str
    key_points: list[str]


class EmailSummarizerAgent(BaseLLMAgent):
    """邮件摘要 Agent。"""

    name = "EmailSummarizerAgent"
    prompt_file = "email_summarizer_agent.txt"

    def summarize(self, email: EmailRecord) -> EmailSummaryResult:
        """根据邮件正文生成短摘要和关键点。"""

        content = self.compact_text(email.body_text or email.snippet or email.subject)
        if not content:
            return EmailSummaryResult(summary="该邮件暂无可分析的正文内容。", key_points=[])

        try:
            return self._summarize_with_llm(email=email)
        except Exception as exc:
            # 模型服务不可用时保留最小兜底，保证用户仍能看到邮件内容预览。
            return self._fallback_summary(content, error=exc)

    def _summarize_with_llm(self, *, email: EmailRecord) -> EmailSummaryResult:
        """调用大模型生成摘要结果。"""

        data = self.run_json(
            user_prompt=(
                "请分析下面这封邮件，生成给办公用户阅读的结构化摘要。\n\n"
                f"{self.build_email_context(email)}"
            ),
        )
        output = self.validate_llm_output(EmailSummaryLLMOutput, data)
        return EmailSummaryResult(
            summary=output.summary,
            key_points=output.key_points,
        )

    def _fallback_summary(self, content: str, *, error: Exception | None = None) -> EmailSummaryResult:
        """模型不可用时的最小兜底摘要。

        这里不再做复杂关键词规则，只把正文前段转成可读摘要，明确告诉用户
        当前结果来自降级逻辑。
        """

        summary = content[:160] + ("..." if len(content) > 160 else "")
        reason = f"原因：{self.error_summary(error)}"
        return EmailSummaryResult(
            summary=f"模型输出校验或调用失败，以下为邮件内容预览：{summary}",
            key_points=[reason[:160]],
        )
