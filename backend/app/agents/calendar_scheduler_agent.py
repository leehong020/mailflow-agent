"""Calendar Scheduler Agent。

第六阶段的会议安排节点。它不直接访问 Google Calendar，而是先调用大模型
从会议邮件中提取结构化会议信息；随后 CalendarService 使用这些信息查询日历
并计算可用时间段。
"""

from dataclasses import dataclass
from email.utils import getaddresses

from app.agents.base import BaseLLMAgent
from app.models.email import EmailRecord
from app.schemas.llm_outputs import CalendarSchedulerLLMOutput


@dataclass(frozen=True)
class CalendarScheduleRequest:
    """Calendar Scheduler Agent 输出的会议安排参数。"""

    meeting_title: str
    participants: list[str]
    duration_minutes: int
    time_window_start: str | None
    time_window_end: str | None
    timezone: str
    location: str
    description: str


class CalendarSchedulerAgent(BaseLLMAgent):
    """会议请求识别与日程参数生成 Agent。"""

    name = "CalendarSchedulerAgent"
    prompt_file = "calendar_scheduler_agent.txt"

    def plan(self, *, email: EmailRecord, duration_minutes: int = 30) -> CalendarScheduleRequest:
        """从会议邮件中提取会议安排参数。"""

        try:
            return self._plan_with_llm(email=email, duration_minutes=duration_minutes)
        except Exception as exc:
            return self._fallback_plan(email=email, duration_minutes=duration_minutes, error=exc)

    def _plan_with_llm(self, *, email: EmailRecord, duration_minutes: int) -> CalendarScheduleRequest:
        """调用大模型解析会议请求。"""

        analysis_summary = email.analysis.summary if email.analysis else ""
        analysis_reason = email.analysis.reason if email.analysis else ""
        data = self.run_json(
            user_prompt=(
                "请从下面这封会议相关邮件中提取会议安排参数。\n\n"
                f"用户请求的会议时长：{duration_minutes} 分钟\n"
                f"邮件分析摘要：{analysis_summary}\n"
                f"邮件分类理由：{analysis_reason}\n\n"
                f"{self.build_email_context(email)}"
            )
        )
        output = self.validate_llm_output(CalendarSchedulerLLMOutput, data)
        participants = self._clean_participants(output.participants or [email.sender])
        return CalendarScheduleRequest(
            meeting_title=output.meeting_title,
            participants=participants,
            duration_minutes=duration_minutes or output.duration_minutes,
            time_window_start=output.time_window_start,
            time_window_end=output.time_window_end,
            timezone=output.timezone,
            location=output.location,
            description=output.description or f"来自邮件：{email.subject}",
        )

    def _fallback_plan(
        self,
        *,
        email: EmailRecord,
        duration_minutes: int,
        error: Exception | None = None,
    ) -> CalendarScheduleRequest:
        """模型不可用时的保守会议参数。

        不做复杂时间推断，只用邮件主题和发件人生成一个可继续查询日历的会议请求。
        """

        description = f"模型输出校验或调用失败，使用邮件基础信息生成日程建议。原因：{self.error_summary(error)}"
        return CalendarScheduleRequest(
            meeting_title=email.subject or "邮件会议请求",
            participants=self._clean_participants([email.sender] if email.sender else []),
            duration_minutes=duration_minutes,
            time_window_start=None,
            time_window_end=None,
            timezone="Asia/Shanghai",
            location="",
            description=description,
        )

    @staticmethod
    def _clean_participants(values: list[str]) -> list[str]:
        """从模型或 Gmail header 中提取纯邮箱地址。

        Gmail 的 From header 可能是 `Alice <alice@example.com>`，而 Calendar
        attendees 只接受邮箱地址，因此这里统一清洗。
        """

        parsed = getaddresses(values)
        emails = [email.strip() for _, email in parsed if email.strip()]
        return list(dict.fromkeys(emails))
