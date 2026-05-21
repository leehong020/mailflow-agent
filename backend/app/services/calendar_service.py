"""Google Calendar 日程服务。

第六阶段的核心业务服务：
1. 读取 Google Calendar 日程；
2. 调用 Calendar Scheduler Agent 从会议邮件提取会议参数；
3. 查询日历 busy 时间段并计算可用时间；
4. 保存 CalendarSuggestion；
5. 创建待确认的 Calendar Event 操作。
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.calendar_scheduler_agent import CalendarScheduleRequest, CalendarSchedulerAgent
from app.models.calendar import CalendarSuggestion
from app.models.draft import PendingAction
from app.models.email import EmailRecord
from app.models.user import User
from app.services.action_service import ActionService
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
        self.action_service = ActionService(db)
        self.google_service = GoogleService(db)
        self.email_service = EmailAnalysisService(db)
        self.scheduler_agent = CalendarSchedulerAgent()

    def list_events(self, *, range_name: str = "today") -> tuple[list[dict], int]:
        """读取今日或本周 Google Calendar 日程。"""

        user = self._current_user()
        start, end = self._range_window(range_name)
        items = self.google_service.list_calendar_events(user=user, time_min=start, time_max=end)
        return items, len(items)

    def get_event(self, *, event_id: str) -> dict:
        """读取单个 Calendar 事件详情。"""

        user = self._current_user()
        return self.google_service.get_calendar_event(user=user, event_id=event_id)

    def create_manual_event_action(
        self,
        *,
        summary: str,
        start: str,
        end: str,
        attendees: list[str],
        description: str = "",
        location: str = "",
        timezone: str = "Asia/Shanghai",
    ) -> PendingAction:
        """创建手动新增 Calendar 事件的待确认操作。"""

        self._ensure_no_event_conflict(
            start=start,
            end=end,
            timezone_name=timezone,
            exclude_event_id=None,
        )
        attendees = self._normalize_attendees(attendees)
        payload = {
            "summary": summary,
            "start": start,
            "end": end,
            "attendees": attendees,
            "description": description,
            "location": location,
            "timezone": timezone,
        }
        preview = {
            "操作": "创建 Google Calendar 日程",
            "标题": summary,
            "开始时间": start,
            "结束时间": end,
            "参会人": attendees,
            "地点": location,
        }
        return self.action_service.create_action(
            action_type="create_calendar_event",
            payload=payload,
            preview=preview,
        )

    def create_update_event_action(
        self,
        *,
        event_id: str,
        summary: str,
        start: str,
        end: str,
        attendees: list[str],
        description: str = "",
        location: str = "",
        timezone: str = "Asia/Shanghai",
    ) -> PendingAction:
        """创建修改 Calendar 事件的待确认操作。

        修改时间属于高风险操作，必须先做冲突检测。检测时会排除当前 event_id，
        避免把“被修改的原事件”误判为冲突。
        """

        old_event = self.get_event(event_id=event_id)
        self._ensure_no_event_conflict(
            start=start,
            end=end,
            timezone_name=timezone,
            exclude_event_id=event_id,
        )
        attendees = self._normalize_attendees(attendees)
        payload = {
            "event_id": event_id,
            "summary": summary,
            "start": start,
            "end": end,
            "attendees": attendees,
            "description": description,
            "location": location,
            "timezone": timezone,
        }
        preview = {
            "操作": "修改 Google Calendar 日程",
            "事件ID": event_id,
            "原标题": old_event.get("summary", ""),
            "新标题": summary,
            "原时间": f"{old_event.get('start', '')} - {old_event.get('end', '')}",
            "新时间": f"{start} - {end}",
            "参会人": attendees,
            "地点": location,
        }
        return self.action_service.create_action(
            action_type="modify_calendar_event",
            payload=payload,
            preview=preview,
        )

    def create_delete_event_action(self, *, event_id: str, reason: str = "") -> PendingAction:
        """创建删除 Calendar 事件的待确认操作。"""

        old_event = self.get_event(event_id=event_id)
        payload = {"event_id": event_id, "reason": reason}
        preview = {
            "操作": "删除 Google Calendar 日程",
            "事件ID": event_id,
            "标题": old_event.get("summary", ""),
            "时间": f"{old_event.get('start', '')} - {old_event.get('end', '')}",
            "参会人": old_event.get("attendees", []),
            "删除原因": reason,
        }
        return self.action_service.create_action(
            action_type="delete_calendar_event",
            payload=payload,
            preview=preview,
        )

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
        preview = {
            "会议标题": suggestion.meeting_title,
            "开始时间": selected_slot["start"],
            "结束时间": selected_slot["end"],
            "参会人": suggestion.participants,
            "地点": suggestion.location,
            "关联邮件": suggestion.source_email_id,
        }
        action = self.action_service.create_action(
            action_type="create_calendar_event",
            payload=payload,
            preview=preview,
        )
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

    def _ensure_no_event_conflict(
        self,
        *,
        start: str,
        end: str,
        timezone_name: str,
        exclude_event_id: str | None,
    ) -> None:
        """校验目标时间段是否和已有 Calendar 事件冲突。"""

        user = self._current_user()
        tz = self._safe_zoneinfo(timezone_name)
        start_at = self._parse_datetime(start, tz)
        end_at = self._parse_datetime(end, tz)
        if start_at is None or end_at is None:
            raise ValueError("日程开始或结束时间格式无效。")
        if end_at <= start_at:
            raise ValueError("日程结束时间必须晚于开始时间。")

        events = self.google_service.list_calendar_events(user=user, time_min=start_at, time_max=end_at)
        for event in events:
            if exclude_event_id and event.get("id") == exclude_event_id:
                continue
            event_start = self._parse_datetime(event.get("start"), tz)
            event_end = self._parse_datetime(event.get("end"), tz)
            if event_start and event_end and self._has_conflict(start_at, end_at, [(event_start, event_end)]):
                title = event.get("summary") or "已有日程"
                raise ValueError(f"该时间段与已有日程“{title}”冲突，请调整时间后再提交。")

    @staticmethod
    def _normalize_attendees(attendees: list[str]) -> list[str]:
        """清洗参会人邮箱，去重并过滤空值。"""

        normalized: list[str] = []
        seen: set[str] = set()
        for item in attendees:
            email = str(item or "").strip()
            if not email or "@" not in email:
                continue
            key = email.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(email)
        return normalized

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
