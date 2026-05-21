"""API 总路由。

这里负责把不同业务模块的路由组合到一起：
- auth：Google OAuth 登录、回调、连接状态；
- dashboard：工作台统计；
- emails：Gmail 最近邮件读取。
"""

from fastapi import APIRouter

from app.api.routes_actions import router as actions_router
from app.api.routes_auth import router as auth_router
from app.api.routes_calendar import router as calendar_router
from app.api.routes_compose import router as compose_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_drafts import router as drafts_router
from app.api.routes_email import router as email_router
from app.api.routes_memory import router as memory_router
from app.api.routes_traces import router as traces_router

# 统一 API 前缀。前端请求都以 /api/v1 开头。
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(actions_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(email_router)
api_router.include_router(drafts_router)
api_router.include_router(compose_router)
api_router.include_router(memory_router)
api_router.include_router(traces_router)
api_router.include_router(calendar_router)
