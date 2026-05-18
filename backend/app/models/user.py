"""用户模型。

第一二阶段只需要保存一个 Google 账号及其 token。
后续如果做多用户、权限系统，可以继续扩展该表，而不需要推翻 OAuth 逻辑。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """当前阶段的 Google 用户与 OAuth token 记录。

    文档中的完整用户体系会在后续阶段扩展；第一二阶段先支持单用户演示，
    但数据结构保留 google_sub，后续可以自然升级为多用户。
    """

    __tablename__ = "users"

    # 使用 UUID 字符串，方便后续和其他表建立关联。
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # email 是当前阶段识别用户的主要字段。
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Google profile 返回的展示信息。
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    picture: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 记录授权 scope，Settings 页面可展示已授权范围。
    google_scopes: Mapped[str] = mapped_column(Text, default="")

    # OAuth token JSON 加密后存储，不能明文入库。
    encrypted_google_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
