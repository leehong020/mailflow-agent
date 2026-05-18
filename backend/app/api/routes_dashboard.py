"""Dashboard 首页接口。

第一阶段先提供可用的占位统计，让前端 Dashboard 能跑通。
后续邮件分析、待确认操作、日程接入后，这里再聚合真实数据。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.auth_service import AuthService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    """第一阶段 Dashboard 占位统计；后续邮件分析阶段会填充真实指标。"""

    # 当前只返回 Google 是否连接，其他数字保持 0，避免前端展示假数据。
    return DashboardSummary(google_connected=AuthService(db).get_current_user() is not None)
