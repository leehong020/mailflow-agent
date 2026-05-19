"""Email Triage Agent。

职责来自开发文档第 9.4 节：
- 判断邮件优先级；
- 识别邮件类型；
- 判断是否需要回复；
- 判断是否涉及会议或待办事项；
- 输出分类理由。
"""

from dataclasses import dataclass

from app.core.llm import LLMClient
from app.models.email import EmailRecord
from app.prompts import EMAIL_TRIAGE_SYSTEM_PROMPT


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


class EmailTriageAgent:
    """邮件分类 Agent。

    分类值严格使用开发文档中的枚举：
    urgent_reply / normal_reply / calendar_related / task_required /
    newsletter / notification / ignore
    """

    name = "EmailTriageAgent"
    system_prompt = EMAIL_TRIAGE_SYSTEM_PROMPT

    urgent_keywords = {
        "urgent",
        "asap",
        "immediately",
        "deadline",
        "due",
        "紧急",
        "尽快",
        "截止",
        "今天",
        "马上",
    }
    reply_keywords = {"please reply", "reply", "respond", "confirm", "回复", "确认", "请回复"}
    meeting_keywords = {
        "meeting",
        "schedule",
        "calendar",
        "call",
        "zoom",
        "meet",
        "会议",
        "日程",
        "开会",
        "时间",
        "视频",
    }
    task_keywords = {
        "todo",
        "task",
        "action item",
        "follow up",
        "complete",
        "finish",
        "待办",
        "任务",
        "完成",
        "跟进",
        "处理",
    }
    newsletter_keywords = {"unsubscribe", "newsletter", "digest", "weekly", "订阅", "周报"}
    notification_keywords = {"notification", "no-reply", "noreply", "alert", "提醒", "通知"}

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

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def triage(self, email: EmailRecord) -> EmailTriageResult:
        """对单封邮件做分类和优先级判断。"""

        text = self._combined_text(email)
        try:
            return self._triage_with_llm(email=email, text=text)
        except Exception:
            return self._triage_with_rules(email=email, text=text)

    def _triage_with_llm(self, *, email: EmailRecord, text: str) -> EmailTriageResult:
        """调用大模型进行邮件分类。"""

        client = self.llm_client or LLMClient()
        data = client.complete_json(
            system_prompt=self.system_prompt,
            user_prompt=(
                f"邮件主题：{email.subject}\n"
                f"发件人：{email.sender}\n"
                f"邮件内容：\n{text[:6000]}\n\n"
                "请判断邮件分类并输出结构化结果。"
            ),
        )
        category = str(data.get("category") or "notification")
        priority = str(data.get("priority") or "low")
        actions = data.get("recommended_actions") or []
        if not isinstance(actions, list):
            actions = []
        return EmailTriageResult(
            category=category if category in self.allowed_categories else "notification",
            priority=priority if priority in self.allowed_priorities else "low",
            need_reply=bool(data.get("need_reply")),
            has_meeting_request=bool(data.get("has_meeting_request")),
            has_task=bool(data.get("has_task")),
            reason=str(data.get("reason") or "模型完成邮件分类。").strip(),
            recommended_actions=[str(item).strip() for item in actions if str(item).strip()][:5],
        )

    def _triage_with_rules(self, *, email: EmailRecord, text: str) -> EmailTriageResult:
        """规则兜底分类。"""

        has_urgent = self._contains(text, self.urgent_keywords)
        need_reply = self._contains(text, self.reply_keywords) or "?" in text or "？" in text
        has_meeting = self._contains(text, self.meeting_keywords)
        has_task = self._contains(text, self.task_keywords) or has_urgent
        is_newsletter = self._contains(text, self.newsletter_keywords)
        is_notification = self._contains(text, self.notification_keywords) or "no-reply" in email.sender.lower()

        category = self._category(
            has_urgent=has_urgent,
            need_reply=need_reply,
            has_meeting=has_meeting,
            has_task=has_task,
            is_newsletter=is_newsletter,
            is_notification=is_notification,
        )
        priority = self._priority(has_urgent=has_urgent, has_meeting=has_meeting, has_task=has_task)
        actions = self._actions(need_reply=need_reply, has_meeting=has_meeting, has_task=has_task)
        reason = self._reason(category, priority, need_reply, has_meeting, has_task)

        return EmailTriageResult(
            category=category,
            priority=priority,
            need_reply=need_reply,
            has_meeting_request=has_meeting,
            has_task=has_task,
            reason=reason,
            recommended_actions=actions,
        )

    @staticmethod
    def _combined_text(email: EmailRecord) -> str:
        return " ".join([email.subject, email.sender, email.snippet, email.body_text]).lower()

    @staticmethod
    def _contains(text: str, keywords: set[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    @staticmethod
    def _category(
        *,
        has_urgent: bool,
        need_reply: bool,
        has_meeting: bool,
        has_task: bool,
        is_newsletter: bool,
        is_notification: bool,
    ) -> str:
        if has_urgent and need_reply:
            return "urgent_reply"
        if has_meeting:
            return "calendar_related"
        if has_task:
            return "task_required"
        if need_reply:
            return "normal_reply"
        if is_newsletter:
            return "newsletter"
        if is_notification:
            return "notification"
        return "ignore"

    @staticmethod
    def _priority(*, has_urgent: bool, has_meeting: bool, has_task: bool) -> str:
        if has_urgent:
            return "high"
        if has_meeting or has_task:
            return "medium"
        return "low"

    @staticmethod
    def _actions(*, need_reply: bool, has_meeting: bool, has_task: bool) -> list[str]:
        actions: list[str] = []
        if need_reply:
            actions.append("生成回复草稿")
        if has_meeting:
            actions.append("查找会议时间")
        if has_task:
            actions.append("创建待办事项")
        if not actions:
            actions.append("标记为已处理")
        return actions

    @staticmethod
    def _reason(
        category: str,
        priority: str,
        need_reply: bool,
        has_meeting: bool,
        has_task: bool,
    ) -> str:
        parts = [f"分类为 {category}", f"优先级为 {priority}"]
        if need_reply:
            parts.append("邮件包含回复或确认意图")
        if has_meeting:
            parts.append("邮件包含会议/日程相关表达")
        if has_task:
            parts.append("邮件包含待办或截止时间信号")
        return "；".join(parts) + "。"
