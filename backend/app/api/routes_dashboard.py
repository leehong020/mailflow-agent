"""Dashboard 首页接口。

第一阶段先提供可用的占位统计，让前端 Dashboard 能跑通。
后续邮件分析、待确认操作、日程接入后，这里再聚合真实数据。
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email import EmailAnalysis, EmailRecord
from app.schemas.dashboard import DashboardSummary
from app.services.auth_service import AuthService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    """Dashboard 汇总统计。"""

    user = AuthService(db).get_current_user()
    if user is None:
        return DashboardSummary(google_connected=False)

    email_count = db.scalar(select(func.count()).where(EmailRecord.user_id == user.id)) or 0
    high_priority_count = (
        db.scalar(
            select(func.count())
            .select_from(EmailAnalysis)
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id, EmailAnalysis.priority == "high")
        )
        or 0
    )
    need_reply_count = (
        db.scalar(
            select(func.count())
            .select_from(EmailAnalysis)
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id, EmailAnalysis.need_reply.is_(True))
        )
        or 0
    )
    meeting_request_count = (
        db.scalar(
            select(func.count())
            .select_from(EmailAnalysis)
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id, EmailAnalysis.has_meeting_request.is_(True))
        )
        or 0
    )

    return DashboardSummary(
        google_connected=True,
        email_count_today=email_count,
        high_priority_count=high_priority_count,
        need_reply_count=need_reply_count,
        meeting_request_count=meeting_request_count,
    )
