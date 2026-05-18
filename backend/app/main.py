"""FastAPI 应用入口。

本文件只做三件事：
1. 创建 FastAPI app；
2. 注册跨域、启动事件和健康检查；
3. 挂载统一的 API 路由。

业务逻辑不要写在这里，后续阶段继续放到 api / services / tools 等目录中。
"""

from fastapi import FastAPI
from fastapi import Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.api.routes_auth import complete_google_callback
from app.core.config import get_settings
from app.db.session import get_db, init_db

settings = get_settings()

# 创建 FastAPI 实例，Swagger 文档会自动出现在 /docs。
app = FastAPI(
    title=settings.app_name,
    description="MailFlow Agent 第一、第二阶段 API：健康检查、Google OAuth、Gmail 最近邮件读取。",
    version="0.2.0",
)

# 允许前端开发服务器访问后端接口。
# 第一二阶段只有本地 Vue dev server，因此 allow_origins 只放 FRONTEND_BASE_URL。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时初始化数据库表。

    当前阶段为了降低启动成本，直接由 SQLAlchemy 自动建表。
    后续进入更完整的企业项目形态时，可以替换为 Alembic 迁移。
    """

    init_db()


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """健康检查接口。

    用于第一阶段验收：后端 uvicorn 启动后访问 /health 应返回 ok。
    """

    return {"status": "ok"}


@app.get("/gmail/auth/callback", tags=["auth"])
def gmail_auth_callback(
    request: Request,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Google Cloud Console 中配置的 OAuth 回调地址。

    你的真实回调地址是：
    http://localhost:8000/gmail/auth/callback
    """

    return complete_google_callback(request=request, state=state, db=db)


# 所有业务 API 都统一挂载在 /api/v1 下，方便后续做版本管理。
app.include_router(api_router)
