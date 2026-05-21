"""Compose Mail Agent。

第十二阶段用于“主动给别人写一封邮件”。它和 ReplyDraftAgent 的边界不同：
ReplyDraftAgent 依赖原邮件上下文，而 ComposeMailAgent 依赖用户输入的写信目标
和当前编辑器内容。两者都输出结构化邮件字段，但职责分开会更容易维护。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.schemas.llm_outputs import ComposeMailLLMOutput


@dataclass(frozen=True)
class ComposeMailResult:
    """Compose Mail Agent 的结构化输出。"""

    to: str
    subject: str
    body: str
    generation_reason: str


class ComposeMailAgent(BaseLLMAgent):
    """主动写邮件 Agent。"""

    name = "ComposeMailAgent"
    prompt_file = "compose_mail_agent.txt"

    def generate(
        self,
        *,
        goal: str,
        to: str = "",
        subject: str = "",
        body: str = "",
        tone: str = "polite",
        language: str = "auto",
    ) -> ComposeMailResult:
        """根据用户写信目标生成一封新邮件。

        current editor state 也会传入模型，这样用户先手写了一部分内容时，
        Agent 可以在现有基础上补全，而不是从零覆盖。
        """

        try:
            return self._generate_with_llm(
                goal=goal,
                to=to,
                subject=subject,
                body=body,
                tone=tone,
                language=language,
            )
        except Exception as exc:
            return self._fallback(goal=goal, to=to, subject=subject, body=body, language=language, error=exc)

    def revise(
        self,
        *,
        instruction: str,
        to: str,
        subject: str,
        body: str,
        tone: str = "polite",
        language: str = "auto",
    ) -> ComposeMailResult:
        """根据用户对话指令修改当前主动写邮件草稿。"""

        try:
            return self._revise_with_llm(
                instruction=instruction,
                to=to,
                subject=subject,
                body=body,
                tone=tone,
                language=language,
            )
        except Exception as exc:
            return ComposeMailResult(
                to=to,
                subject=subject,
                body=body,
                generation_reason=f"AI 修改失败，已保留原草稿内容。原因：{BaseLLMAgent.error_summary(exc, limit=120)}",
            )

    def _generate_with_llm(
        self,
        *,
        goal: str,
        to: str,
        subject: str,
        body: str,
        tone: str,
        language: str,
    ) -> ComposeMailResult:
        """调用大模型生成主动写邮件草稿。"""

        data = self.run_json(
            user_prompt=(
                "请根据用户写信目标生成一封新邮件，并返回结构化字段。\n\n"
                f"写信目标：{goal}\n"
                f"语气：{tone}\n"
                f"语言：{language}\n\n"
                "当前编辑器内容，如果为空则从写信目标生成：\n"
                f"To: {to}\n"
                f"Subject: {subject}\n"
                f"Body:\n{body}"
            ),
        )
        output = self.validate_llm_output(ComposeMailLLMOutput, data)
        return ComposeMailResult(
            to=output.to or to,
            subject=output.subject,
            body=output.body,
            generation_reason=output.generation_reason,
        )

    def _revise_with_llm(
        self,
        *,
        instruction: str,
        to: str,
        subject: str,
        body: str,
        tone: str,
        language: str,
    ) -> ComposeMailResult:
        """调用大模型按用户要求修改主动写邮件草稿。"""

        data = self.run_json(
            user_prompt=(
                "请根据用户修改要求更新当前邮件草稿。必须保留用户没有要求改变的关键信息。\n\n"
                f"修改要求：{instruction}\n"
                f"语气：{tone}\n"
                f"语言：{language}\n\n"
                "当前草稿：\n"
                f"To: {to}\n"
                f"Subject: {subject}\n"
                f"Body:\n{body}"
            ),
        )
        output = self.validate_llm_output(ComposeMailLLMOutput, data)
        return ComposeMailResult(
            to=output.to or to,
            subject=output.subject or subject,
            body=output.body,
            generation_reason=output.generation_reason,
        )

    @staticmethod
    def _fallback(
        *,
        goal: str,
        to: str,
        subject: str,
        body: str,
        language: str,
        error: Exception | None,
    ) -> ComposeMailResult:
        """模型不可用时的安全兜底。

        兜底不会假装理解复杂需求，只把用户目标整理成一封最基础的邮件，
        并在 generation_reason 中明确说明模型调用失败。
        """

        if body.strip():
            draft_body = body
        elif language.lower().startswith("en"):
            draft_body = f"Hi,\n\n{goal.strip()}\n\nBest regards,"
        else:
            draft_body = f"你好，\n\n{goal.strip()}\n\n此致\n敬礼"
        fallback_subject = subject.strip() or BaseLLMAgent.truncate(goal.strip(), 30) or "(无主题)"
        reason = f"模型调用失败，已根据写信目标生成基础草稿。原因：{BaseLLMAgent.error_summary(error, limit=120)}"
        return ComposeMailResult(to=to.strip(), subject=fallback_subject, body=draft_body, generation_reason=reason)
