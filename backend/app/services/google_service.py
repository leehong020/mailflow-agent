"""Google 业务服务。

该层连接 AuthService 和 GmailTool：
1. 从数据库读取加密 token；
2. 解密并恢复 Google Credentials；
3. token 过期时自动刷新并重新保存；
4. 调用 GmailTool 获取邮件。
"""

import json

from google.oauth2.credentials import Credentials
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.security import encrypt_text
from app.models.user import User
from app.services.auth_service import AuthService
from app.tools.google_calendar_tool import GoogleCalendarTool
from app.tools.gmail_tool import GmailTool


class GoogleService:
    """Google 账号相关业务编排：凭证刷新、用户信息读取、Gmail 调用。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)

    def get_user_profile(self, credentials) -> dict:
        """通过 Google OAuth2 API 读取当前授权用户资料。"""

        service = build("oauth2", "v2", credentials=credentials, cache_discovery=False)
        return service.userinfo().get().execute()

    def credentials_for_user(self, user: User) -> Credentials:
        """将数据库中的 token 恢复成 Google Credentials。"""

        token_json = self.auth_service.get_decrypted_token_json(user)
        credentials = Credentials.from_authorized_user_info(json.loads(token_json))

        # access_token 有有效期；如果过期且存在 refresh_token，就自动刷新。
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except (GoogleAuthError, TransportError) as exc:
                raise RuntimeError("刷新 Google token 失败，请重新连接 Google 账号。") from exc
            user.encrypted_google_token = encrypt_text(credentials.to_json())
            self.db.commit()
        return credentials

    def list_recent_emails(self, limit: int = 20) -> list[dict]:
        """读取当前连接账号的 Gmail 最近邮件。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).list_recent_messages(limit=limit)
        except Exception as exc:
            raise RuntimeError("读取 Gmail 邮件失败，请确认 Gmail API 已启用且账号已授予读取权限。") from exc

    def create_gmail_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        """创建 Gmail 草稿。

        第五阶段只创建草稿，不发送邮件。
        """

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).create_draft(to=to, subject=subject, body=body)
        except Exception as exc:
            raise RuntimeError("创建 Gmail 草稿失败，请确认已授予 gmail.compose 权限。") from exc

    def send_gmail_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        """发送 Gmail 邮件。

        该方法必须通过 Pending Actions 确认后调用。
        """

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).send_message(to=to, subject=subject, body=body)
        except Exception as exc:
            raise RuntimeError("发送 Gmail 邮件失败，请确认已授予 gmail.send 权限。") from exc

    def list_gmail_labels(self) -> list[dict]:
        """读取 Gmail 标签列表。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).list_labels()
        except Exception as exc:
            raise RuntimeError("读取 Gmail 标签失败，请确认已授予 gmail.modify 权限。") from exc

    def modify_gmail_message(
        self,
        *,
        gmail_message_id: str,
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict:
        """修改单封 Gmail 邮件标签。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).modify_message_labels(
                message_id=gmail_message_id,
                add_label_ids=add_label_ids,
                remove_label_ids=remove_label_ids,
            )
        except Exception as exc:
            raise RuntimeError("修改 Gmail 邮件失败，请确认已授予 gmail.modify 权限。") from exc

    def trash_gmail_message(self, *, gmail_message_id: str) -> dict:
        """移动单封 Gmail 邮件到垃圾箱。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).trash_message(message_id=gmail_message_id)
        except Exception as exc:
            raise RuntimeError("移动 Gmail 邮件到垃圾箱失败，请确认已授予 gmail.modify 权限。") from exc

    def batch_modify_gmail_messages(
        self,
        *,
        gmail_message_ids: list[str],
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> dict:
        """批量修改 Gmail 邮件标签。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GmailTool(credentials).batch_modify_messages(
                message_ids=gmail_message_ids,
                add_label_ids=add_label_ids,
                remove_label_ids=remove_label_ids,
            )
        except Exception as exc:
            raise RuntimeError("批量修改 Gmail 邮件失败，请确认已授予 gmail.modify 权限。") from exc

    def list_calendar_events(self, *, user: User, time_min, time_max) -> list[dict]:
        """读取 Google Calendar 指定范围内的日程。"""

        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).list_events(time_min=time_min, time_max=time_max)
        except Exception as exc:
            raise RuntimeError("读取 Google Calendar 失败，请确认 Calendar API 已启用且账号已授予日历读取权限。") from exc

    def get_calendar_event(self, *, user: User, event_id: str) -> dict:
        """读取单个 Google Calendar 事件详情。"""

        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).get_event(event_id=event_id)
        except Exception as exc:
            raise RuntimeError("读取 Google Calendar 日程详情失败，请确认事件存在且账号有读取权限。") from exc

    def query_calendar_busy(self, *, user: User, time_min, time_max) -> list[dict]:
        """查询 Google Calendar 中已占用的时间段。"""

        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).query_busy(time_min=time_min, time_max=time_max)
        except Exception as exc:
            raise RuntimeError("查询 Google Calendar 空闲时间失败，请确认已授予日历权限。") from exc

    def create_calendar_event(
        self,
        *,
        summary: str,
        start: str,
        end: str,
        attendees: list[str],
        description: str = "",
        location: str = "",
        timezone: str = "Asia/Shanghai",
    ) -> dict:
        """创建 Google Calendar 事件。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).create_event(
                summary=summary,
                start=start,
                end=end,
                attendees=attendees,
                description=description,
                location=location,
                timezone=timezone,
            )
        except Exception as exc:
            raise RuntimeError("创建 Google Calendar 日程失败，请确认已授予 calendar.events 权限。") from exc

    def update_calendar_event(
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
    ) -> dict:
        """修改 Google Calendar 事件。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).update_event(
                event_id=event_id,
                summary=summary,
                start=start,
                end=end,
                attendees=attendees,
                description=description,
                location=location,
                timezone=timezone,
            )
        except Exception as exc:
            raise RuntimeError("修改 Google Calendar 日程失败，请确认已授予 calendar.events 权限。") from exc

    def delete_calendar_event(self, *, event_id: str) -> dict:
        """删除 Google Calendar 事件。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        try:
            return GoogleCalendarTool(credentials).delete_event(event_id=event_id)
        except Exception as exc:
            raise RuntimeError("删除 Google Calendar 日程失败，请确认已授予 calendar.events 权限。") from exc
