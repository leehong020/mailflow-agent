"""认证相关响应结构。

Pydantic schema 用于约束 API 返回值，保证前端拿到稳定字段。
"""

from pydantic import BaseModel


class GoogleConnectionStatus(BaseModel):
    """Settings 页面展示 Google 连接状态所需的数据。"""

    connected: bool
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    scopes: list[str] = []
