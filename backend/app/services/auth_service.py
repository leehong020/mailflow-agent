"""认证业务服务。

Service 层承接业务规则：
- 当前用户如何查询；
- Google 用户如何保存；
- token 如何加密后入库；
- 断开连接时如何仅清除授权 token，并保留本地分析数据。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_text, encrypt_text
from app.models.user import User


class AuthService:
    """处理用户与 Google token 的本地持久化。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_current_user(self) -> User | None:
        """获取当前演示账号。

        第一二阶段暂不做复杂登录态，默认取最近更新且仍保存 token 的 Google 用户。
        这样课程演示时一个浏览器即可完整跑通。
        """

        return self.db.scalars(
            select(User)
            .where(User.encrypted_google_token != "")
            .order_by(User.updated_at.desc())
        ).first()

    def save_google_user(self, profile: dict, credentials) -> User:
        """保存或更新 Google 用户资料与 OAuth token。"""

        email = profile.get("email")
        if not email:
            raise ValueError("Google 用户信息中没有 email，无法保存账号。")

        user = self.db.scalars(select(User).where(User.email == email)).first()
        if user is None:
            user = User(email=email, encrypted_google_token="")
            self.db.add(user)

        # 用户资料用于 Settings 页面展示。
        user.name = profile.get("name")
        user.google_sub = profile.get("id")
        user.picture = profile.get("picture")
        user.google_scopes = ",".join(credentials.scopes or [])
        # credentials.to_json() 包含 access_token、refresh_token、过期时间等。
        # 写入数据库前必须加密。
        user.encrypted_google_token = encrypt_text(credentials.to_json())
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_decrypted_token_json(self, user: User) -> str:
        """读取并解密数据库中的 Google token JSON。"""

        return decrypt_text(user.encrypted_google_token)

    def disconnect_google(self) -> None:
        """断开 Google 授权，但保留本地邮件、分析、草稿和轨迹数据。

        之前这里会删除 User 以及该用户下的全部工作区数据，导致用户为了新增
        scope 重新授权后，已经分析过的邮件全部变成“未分析”。现在只清空本地
        token 和 scope：Settings 会显示未连接；重新连接同一邮箱时会复用同一个
        User 记录，因此 email_analysis / tasks 等历史结果仍然能通过 user_id 找到。
        """

        user = self.get_current_user()
        if user is None:
            return
        user.encrypted_google_token = ""
        user.google_scopes = ""
        self.db.commit()
