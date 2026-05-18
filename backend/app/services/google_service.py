"""Google 业务服务。

该层连接 AuthService 和 GmailTool：
1. 从数据库读取加密 token；
2. 解密并恢复 Google Credentials；
3. token 过期时自动刷新并重新保存；
4. 调用 GmailTool 获取邮件。
"""

import json

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.security import encrypt_text
from app.models.user import User
from app.services.auth_service import AuthService
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
            credentials.refresh(Request())
            user.encrypted_google_token = encrypt_text(credentials.to_json())
            self.db.commit()
        return credentials

    def list_recent_emails(self, limit: int = 20) -> list[dict]:
        """读取当前连接账号的 Gmail 最近邮件。"""

        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        credentials = self.credentials_for_user(user)
        return GmailTool(credentials).list_recent_messages(limit=limit)
