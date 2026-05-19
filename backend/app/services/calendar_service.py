"""Google Calendar 日程服务。

第六阶段的核心业务服务：
1. 读取 Google Calendar 日程；
2. 调用 Calendar Scheduler Agent 从会议邮件提取会议参数；
3. 查询日历 busy 时间段并计算可用时间；
4. 保存 CalendarSuggestion；
5. 创建待确认的 Calendar Event 操作。
"""

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.calendar_scheduler_agent import CalendarScheduleRequest, CalendarSchedulerAgent
from app.models.calendar import CalendarSuggestion
from app.models.draft import PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.email_analysis_service import EmailAnalysisService
from app.services.google_service import GoogleService


@dataclass(frozen=True)
class SuggestedSlot:
    """后端内部使用的推荐时间段。"""

    start: str
    end: str
    reason: str


class CalendarService:
    """日程读取、会议建议和待确认日程操作服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.google_service = GoogleService(db)
        self.email_service = EmailAnalysisService(db)
        self.scheduler_agent = CalendarSchedulerAgent()

    def list_events(self, *, range_name: str = "today") -> tuple[list[dict], int]:
        """读取今日或本周 Google Calendar 日程。"""

        user = self._current_user()
        start, end = self._range_window(range_name)
        items = self.google_service.list_calendar_events(user=user, time_min=start, time_max=end)
        return items, len(items)

    def list_suggestions(self, *, limit: int = 20, offset: int = 0) -> tuple[list[CalendarSuggestion], int]:
        """查询当前用户已生成的日程建议。"""

        user = self._current_user()
        query = (
            select(CalendarSuggestion)
            .where(CalendarSuggestion.user_id == user.id)
            .order_by(CalendarSuggestion.created_at.desc())
        )
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.offset(offset).limit(limit)).all()
        return list(items), total

    def get_suggestion(self, suggestion_id: str) -> CalendarSuggestion | None:
        """查询单个日程建议。"""

        user = self._current_user()
        return self.db.scalars(
            select(CalendarSuggestion).where(
                CalendarSuggestion.id == suggestion_id,
                CalendarSuggestion.user_id == user.id,
            )
        ).first()

    def suggest_slots(self, *, email_id: str, duration_minutes: int = 30) -> CalendarSuggestion:
        """从会议邮件生成可用时间建议。"""

        user = self._current_user()
        email = self.email_service.get_email_detail(email_id)
        if email is None:
            raise ValueError("邮件不存在。")

        plan = self.scheduler_agent.plan(email=email, duration_minutes=duration_minutes)
        window_start, window_end = self._plan_window(plan)
        busy_items = self.google_service.query_calendar_busy(user=user, time_min=window_start, time_max=window_end)
        slots = self._find_available_slots(
            window_start=window_start,
            window_end=window_end,
            busy_items=busy_items,
            duration_minutes=plan.duration_minutes,
            timezone_name=plan.timezone,
        )

        suggestion = CalendarSuggestion(
            user_id=user.id,
            source_email_id=email.id,
            meeting_title=plan.meeting_title,
            description=plan.description,
            location=plan.location,
            timezone=plan.timezone,
            duration_minutes=plan.duration_minutes,
            participants=plan.participants,
            suggested_slots=[slot.__dict__ for slot in slots],
            status="suggested",
        )
        self.db.add(suggestion)
        self.db.flush()
        return suggestion

    def create_pending_action(self, *, suggestion: CalendarSuggestion, selected_slot: dict) -> PendingAction:
        """把用户选择的日程创建操作放入 Pending Actions。"""

        user = self._current_user()
        if suggestion.user_id != user.id:
            raise ValueError("日程建议不存在。")

        self._ensure_slot_belongs_to_suggestion(suggestion=suggestion, selected_slot=selected_slot)
        suggestion.selected_slot = selected_slot
        suggestion.status = "pending"

        payload = {
            "suggestion_id": suggestion.id,
            "summary": suggestion.meeting_title,
            "description": suggestion.description,
            "location": suggestion.location,
            "timezone": suggestion.timezone,
            "attendees": suggestion.participants,
            "start": selected_slot["start"],
            "end": selected_slot["end"],
        }
        action = PendingAction(
            user_id=user.id,
            action_type="create_calendar_event",
            payload=json.dumps(payload, ensure_ascii=False),
            preview=json.dumps(payload, ensure_ascii=False),
            risk_level="high",
        )
        self.db.add(action)
        self.db.flush()
        return action

    def _current_user(self) -> User:
        """获取当前连接的 Google 用户。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user

    @staticmethod
    def _range_window(range_name: str) -> tuple[datetime, datetime]:
        """把 today/week 转换成 Calendar API 查询窗口。"""

        now = datetime.now().astimezone()
        day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        if range_name == "week":
            return day_start, day_start + timedelta(days=7)
        return day_start, day_start + timedelta(days=1)

    def _plan_window(self, plan: CalendarScheduleRequest) -> tuple[datetime, datetime]:
        """根据 Agent 输出决定查询日历的时间窗口。"""

        tz = self._safe_zoneinfo(plan.timezone)
        start = self._parse_datetime(plan.time_window_start, tz)
        end = self._parse_datetime(plan.time_window_end, tz)
        now = datetime.now(tz)
        if start is None or start < now:
            start = now + timedelta(hours=1)
        if end is None or end <= start:
            end = start + timedelta(days=7)
        return start, end

    def _find_available_slots(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        busy_items: list[dict],
        duration_minutes: int,
        timezone_name: str,
    ) -> list[SuggestedSlot]:
        """根据 busy 时间段计算可用时间。

        为了让建议更符合办公场景，默认只在工作日 09:00-18:00 内搜索，
        每 30 分钟尝试一个候选起点。
        """

        tz = self._safe_zoneinfo(timezone_name)
        busy_ranges = [
            (self._parse_datetime(item.get("start"), tz), self._parse_datetime(item.get("end"), tz))
            for item in busy_items
        ]
        busy_ranges = [(start, end) for start, end in busy_ranges if start and end]
        duration = timedelta(minutes=duration_minutes)
        step = timedelta(minutes=30)
        slots: list[SuggestedSlot] = []

        current_day = window_start.astimezone(tz).date()
        last_day = window_end.astimezone(tz).date()
        while current_day <= last_day and len(slots) < 5:
            # 周六周日默认不推荐，避免把私人时间推给用户。
            if current_day.weekday() >= 5:
                current_day += timedelta(days=1)
                continue

            day_start = datetime.combine(current_day, time(hour=9), tzinfo=tz)
            day_end = datetime.combine(current_day, time(hour=18), tzinfo=tz)
            cursor = max(day_start, window_start.astimezone(tz))
            while cursor + duration <= min(day_end, window_end.astimezone(tz)) and len(slots) < 5:
                candidate_end = cursor + duration
                if not self._has_conflict(cursor, candidate_end, busy_ranges):
                    slots.append(
                        SuggestedSlot(
                            start=cursor.isoformat(),
                            end=candidate_end.isoformat(),
                            reason="该时间段没有已有会议，且位于工作时间内。",
                        )
                    )
                cursor += step
            current_day += timedelta(days=1)

        return slots

    @staticmethod
    def _has_conflict(start: datetime, end: datetime, busy_ranges: list[tuple[datetime, datetime]]) -> bool:
        """判断候选时间段是否和已有日程重叠。"""

        for busy_start, busy_end in busy_ranges:
            if start < busy_end and end > busy_start:
                return True
        return False

    @staticmethod
    def _parse_datetime(value: str | None, tz: ZoneInfo) -> datetime | None:
        """解析 ISO 时间；无法解析时返回 None。"""

        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=tz)
        return parsed.astimezone(tz)

    @staticmethod
    def _safe_zoneinfo(timezone_name: str) -> ZoneInfo:
        """把用户或模型给出的时区转换成 ZoneInfo，失败时使用上海时区。"""

        try:
            return ZoneInfo(timezone_name)
        except Exception:
            return ZoneInfo("Asia/Shanghai")

    @staticmethod
    def _ensure_slot_belongs_to_suggestion(*, suggestion: CalendarSuggestion, selected_slot: dict) -> None:
        """确保用户选择的时间段来自系统推荐，避免前端伪造任意时间。"""

        start = selected_slot.get("start")
        end = selected_slot.get("end")
        if not start or not end:
            raise ValueError("请选择有效时间段。")
        for slot in suggestion.suggested_slots:
            if slot.get("start") == start and slot.get("end") == end:
                return
        raise ValueError("所选时间段不属于该日程建议。")
