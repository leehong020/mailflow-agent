"""Email Triage Agent。

该 Agent 负责邮件分类、优先级和处理建议。主实现交给大模型完成：
代码只负责提供完整上下文、约束枚举值、清洗模型输出。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.models.email import EmailRecord
from app.schemas.llm_outputs import EmailTriageLLMOutput


@dataclass(frozen=True)
class EmailTriageResult:
    """分类 Agent 的结构化输出。"""

    category: str
    priority: str
    need_reply: bool
    has_meeting_request: bool
    has_task: bool
    reason: str
    recommended_actions: list[str]


class EmailTriageAgent(BaseLLMAgent):
    """邮件分类 Agent。

    分类值严格使用开发文档中的枚举：
    urgent_reply / normal_reply / calendar_related / task_required /
    newsletter / notification / ignore
    """

    name = "EmailTriageAgent"
    prompt_file = "email_triage_agent.txt"

    allowed_categories = {
        "urgent_reply",
        "normal_reply",
        "calendar_related",
        "task_required",
        "newsletter",
        "notification",
        "ignore",
    }
    allowed_priorities = {"high", "medium", "low"}

    def triage(self, email: EmailRecord) -> EmailTriageResult:
        """对单封邮件做分类和优先级判断。"""

        try:
            return self._triage_with_llm(email=email)
        except Exception as exc:
            return self._fallback_triage(email=email, error=exc)

    def _triage_with_llm(self, *, email: EmailRecord) -> EmailTriageResult:
        """调用大模型进行邮件分类。"""

        data = self.run_json(
            user_prompt=(
                "请像企业办公助理一样对下面这封邮件进行分诊，输出分类、优先级和建议动作。\n\n"
                f"{self.build_email_context(email)}"
            ),
        )
        output = self.validate_llm_output(EmailTriageLLMOutput, data)
        return EmailTriageResult(
            category=output.category,
            priority=output.priority,
            need_reply=output.need_reply,
            has_meeting_request=output.has_meeting_request,
            has_task=output.has_task,
            reason=output.reason,
            recommended_actions=output.recommended_actions,
        )

    def _fallback_triage(self, *, email: EmailRecord, error: Exception | None = None) -> EmailTriageResult:
        """模型不可用时的保守兜底分类。

        不再用关键词规则推断业务语义，而是把邮件放入待人工查看的普通回复队列。
        这样不会因为本地规则误判而自动触发高风险动作。
        """

        has_content = bool(self.compact_text(email.body_text or email.snippet or email.subject))
        reason = "模型输出校验或调用失败，系统未做语义推断，建议人工查看后处理。"
        if error:
            reason = f"{reason}原因：{self.error_summary(error, limit=120)}"
        return EmailTriageResult(
            category="normal_reply" if has_content else "ignore",
            priority="medium" if has_content else "low",
            need_reply=False,
            has_meeting_request=False,
            has_task=False,
            reason=reason,
            recommended_actions=["人工查看邮件详情"],
        )
