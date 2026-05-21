"""Reply Draft Agent。

开发文档第五阶段要求实现回复草稿生成。当前主路径是大模型根据邮件上下文、
摘要、分类理由、用户选择的语气和语言生成 JSON 草稿；本地模板只作为模型
不可用时的兜底。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.models.email import EmailRecord
from app.schemas.llm_outputs import ReplyDraftLLMOutput


@dataclass(frozen=True)
class ReplyDraftResult:
    """Reply Draft Agent 的结构化输出。"""

    to: str
    subject: str
    body: str
    generation_reason: str


class ReplyDraftAgent(BaseLLMAgent):
    """回复草稿生成 Agent。"""

    name = "ReplyDraftAgent"
    prompt_file = "reply_draft_agent.txt"

    def draft(self, *, email: EmailRecord, tone: str = "polite", language: str = "en") -> ReplyDraftResult:
        """生成一封可审核的回复草稿。"""

        try:
            return self._draft_with_llm(email=email, tone=tone, language=language)
        except Exception as exc:
            return self._draft_with_rules(email=email, tone=tone, language=language, error=exc)

    def _draft_with_llm(self, *, email: EmailRecord, tone: str, language: str) -> ReplyDraftResult:
        """调用大模型生成草稿。"""

        analysis_summary = email.analysis.summary if email.analysis else ""
        analysis_reason = email.analysis.reason if email.analysis else ""
        data = self.run_json(
            user_prompt=(
                "请根据下面的邮件内容和用户本次要求生成一封待审核回复草稿。\n\n"
                f"回复语气：{tone}\n"
                f"回复语言：{language}\n"
                f"邮件分析摘要：{analysis_summary}\n"
                f"邮件分类理由：{analysis_reason}\n\n"
                f"{self.build_email_context(email)}"
            ),
        )
        output = self.validate_llm_output(ReplyDraftLLMOutput, data)
        return ReplyDraftResult(
            to=output.to,
            subject=self._subject(output.subject, email.subject),
            body=output.body,
            generation_reason=output.generation_reason,
        )

    def revise(
        self,
        *,
        email: EmailRecord | None,
        to: str,
        subject: str,
        body: str,
        instruction: str,
        tone: str = "polite",
        language: str = "auto",
    ) -> ReplyDraftResult:
        """根据用户自然语言要求修改当前草稿。

        该方法用于第十一阶段 AI 回复工作台。它不会创建外部 Gmail 草稿，
        只返回新的编辑器内容，由 DraftService 保存到本地 DraftPreview。
        """

        try:
            return self._revise_with_llm(
                email=email,
                to=to,
                subject=subject,
                body=body,
                instruction=instruction,
                tone=tone,
                language=language,
            )
        except Exception as exc:
            return ReplyDraftResult(
                to=to,
                subject=subject,
                body=body,
                generation_reason=f"AI 修改失败，已保留原草稿内容。原因：{BaseLLMAgent.error_summary(exc, limit=120)}",
            )

    def _revise_with_llm(
        self,
        *,
        email: EmailRecord | None,
        to: str,
        subject: str,
        body: str,
        instruction: str,
        tone: str,
        language: str,
    ) -> ReplyDraftResult:
        """调用大模型按用户修改要求重写草稿。"""

        email_context = self.build_email_context(email) if email is not None else "无原始邮件上下文。"
        data = self.run_json(
            user_prompt=(
                "请根据用户的修改要求，更新当前邮件草稿。必须保留用户没有要求改变的关键信息。\n\n"
                f"回复语气：{tone}\n"
                f"回复语言：{language}\n"
                f"用户修改要求：{instruction}\n\n"
                "当前草稿：\n"
                f"To: {to}\n"
                f"Subject: {subject}\n"
                f"Body:\n{body}\n\n"
                f"原始邮件上下文：\n{email_context}"
            ),
        )
        output = self.validate_llm_output(ReplyDraftLLMOutput, data)
        return ReplyDraftResult(
            to=output.to or to,
            subject=output.subject or subject,
            body=output.body,
            generation_reason=output.generation_reason,
        )

    def _draft_with_rules(
        self,
        *,
        email: EmailRecord,
        tone: str,
        language: str,
        error: Exception | None = None,
    ) -> ReplyDraftResult:
        """大模型不可用时的模板兜底。"""

        subject = self._subject("", email.subject)
        if language.lower().startswith("zh"):
            body = "你好，\n\n感谢你的来信。我已经阅读了邮件内容，会尽快跟进并回复你。\n\n此致\nMailFlow Agent"
        else:
            body = (
                "Hi,\n\n"
                "Thank you for your email. I have reviewed your message and will follow up accordingly.\n\n"
                "Best regards,\nMailFlow Agent"
            )
        return ReplyDraftResult(
            to=email.sender,
            subject=subject,
            body=body,
            generation_reason=self._fallback_reason(tone=tone, error=error),
        )

    @staticmethod
    def _fallback_reason(*, tone: str, error: Exception | None = None) -> str:
        """生成带校验失败原因的兜底说明。"""

        reason = f"模型输出校验或调用失败，基于 {tone} 语气生成基础回复模板。"
        if error:
            reason = f"{reason}原因：{BaseLLMAgent.error_summary(error, limit=120)}"
        return reason

    @staticmethod
    def _empty_body(language: str) -> str:
        """模型返回空正文时的安全占位。"""

        if language.lower().startswith("zh"):
            return "你好，\n\n我已收到你的邮件，会进一步确认后回复你。\n\n此致"
        return "Hi,\n\nThank you for your email. I will review the details and follow up.\n\nBest regards,"

    @staticmethod
    def _subject(generated_subject: str, source_subject: str) -> str:
        """保证回复主题带 Re: 前缀。"""

        subject = generated_subject.strip() or source_subject or "(无主题)"
        if subject.lower().startswith("re:"):
            return subject
        return f"Re: {subject}"
