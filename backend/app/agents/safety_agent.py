"""Safety Agent。

第七阶段 Human-in-the-loop 的核心规则：
所有会影响外部世界的操作，都不能由系统自动执行，必须先进入 Pending Actions，
等待用户明确点击确认。

当前第一版不需要调用大模型，因为安全策略应当稳定、可解释、可审计。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SafetyDecision:
    """Safety Agent 对一次外部操作的判断结果。"""

    requires_confirmation: bool
    risk_level: str
    reason: str


class SafetyAgent:
    """高风险操作拦截 Agent。"""

    name = "SafetyAgent"

    high_risk_actions = {
        "create_calendar_event",
        "delete_calendar_event",
        "send_email",
        "modify_calendar_event",
        "trash_email",
        "batch_email_operation",
    }
    medium_risk_actions = {"create_gmail_draft", "archive_email", "modify_email_labels"}

    def assess(self, *, action_type: str, payload: dict[str, Any]) -> SafetyDecision:
        """评估外部操作风险。

        Args:
            action_type: 操作类型，例如 create_gmail_draft。
            payload: 即将提交给 Gmail / Calendar 工具的参数。

        Returns:
            SafetyDecision。第七阶段默认所有外部可见操作都需要确认。
        """

        if action_type in self.high_risk_actions:
            return SafetyDecision(
                requires_confirmation=True,
                risk_level="high",
                reason="该操作会影响外部 Google 数据，可能隐藏、移动或创建重要信息，必须由用户确认。",
            )
        if action_type in self.medium_risk_actions:
            return SafetyDecision(
                requires_confirmation=True,
                risk_level="medium",
                reason="该操作会在 Gmail 中创建草稿，虽然不会自动发送，但仍需用户确认。",
            )
        return SafetyDecision(
            requires_confirmation=True,
            risk_level="high",
            reason=f"未知外部操作 {action_type}，按高风险处理并要求用户确认。",
        )
