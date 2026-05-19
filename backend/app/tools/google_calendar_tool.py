"""Google Calendar API 工具层。

Tool 层只负责和 Google Calendar API 通信，不处理数据库和 HTTP 异常。
Service 层会把这里返回的原始结构整理成前端需要的响应。
"""

from datetime import datetime
from typing import Any

from googleapiclient.discovery import build


class GoogleCalendarTool:
    """Google Calendar API 的最小封装。

    第六阶段需要三类能力：
    1. 读取日程；
    2. 查询 busy/freebusy 信息；
    3. 用户确认后创建 Calendar event。
    """

    def __init__(self, credentials) -> None:
        self.service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def list_events(self, *, time_min: datetime, time_max: datetime, max_results: int = 50) -> list[dict[str, Any]]:
        """读取指定时间范围内的主日历事件。"""

        response = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [self._event_item(item) for item in response.get("items", [])]

    def query_busy(self, *, time_min: datetime, time_max: datetime) -> list[dict[str, str]]:
        """查询指定范围内已经被占用的时间段。"""

        response = (
            self.service.freebusy()
            .query(
                body={
                    "timeMin": time_min.isoformat(),
                    "timeMax": time_max.isoformat(),
                    "items": [{"id": "primary"}],
                }
            )
            .execute()
        )
        calendars = response.get("calendars", {})
        primary = calendars.get("primary", {})
        return primary.get("busy", [])

    def create_event(
        self,
        *,
        summary: str,
        start: str,
        end: str,
        attendees: list[str],
        description: str = "",
        location: str = "",
        timezone: str = "Asia/Shanghai",
    ) -> dict[str, Any]:
        """在主日历中创建会议事件。"""

        body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start, "timeZone": timezone},
            "end": {"dateTime": end, "timeZone": timezone},
            "attendees": [{"email": item} for item in attendees if item],
        }
        return self.service.events().insert(calendarId="primary", body=body).execute()

    @staticmethod
    def _event_item(raw: dict[str, Any]) -> dict[str, Any]:
        """把 Google event 统一成前端和冲突检测需要的结构。"""

        start = raw.get("start", {})
        end = raw.get("end", {})
        attendees = raw.get("attendees", [])
        return {
            "id": raw.get("id", ""),
            "summary": raw.get("summary", "(无标题日程)"),
            "description": raw.get("description", ""),
            "location": raw.get("location", ""),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "html_link": raw.get("htmlLink", ""),
            "attendees": [item.get("email", "") for item in attendees if item.get("email")],
        }
