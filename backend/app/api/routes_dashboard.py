"""Dashboard 首页接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.calendar import CalendarSuggestion
from app.models.draft import DraftPreview, PendingAction
from app.models.email import EmailAnalysis, EmailRecord, TaskItem
from app.models.trace import AgentTrace
from app.models.user import User
from app.schemas.dashboard import DashboardBreakdownItem, DashboardRecentItem, DashboardSummary
from app.services.auth_service import AuthService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    """Dashboard 汇总统计。"""

    user = AuthService(db).get_current_user()
    if user is None:
        return DashboardSummary(google_connected=False)

    email_count = db.scalar(select(func.count()).where(EmailRecord.user_id == user.id)) or 0
    analyzed_email_count = (
        db.scalar(
            select(func.count())
            .select_from(EmailAnalysis)
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id)
        )
        or 0
    )
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
    task_count = db.scalar(select(func.count()).where(TaskItem.user_id == user.id)) or 0
    pending_action_count = (
        db.scalar(
            select(func.count()).where(
                PendingAction.user_id == user.id,
                PendingAction.status == "pending",
            )
        )
        or 0
    )
    calendar_suggestion_count = (
        db.scalar(select(func.count()).where(CalendarSuggestion.user_id == user.id))
        or 0
    )
    draft_preview_count = db.scalar(select(func.count()).where(DraftPreview.user_id == user.id)) or 0
    trace_count = db.scalar(select(func.count()).where(AgentTrace.user_id == user.id)) or 0
    today_event_count = (
        db.scalar(
            select(func.count()).where(
                CalendarSuggestion.user_id == user.id,
                CalendarSuggestion.status.in_(["pending", "created"]),
            )
        )
        or 0
    )

    return DashboardSummary(
        google_connected=True,
        email_count_today=email_count,
        analyzed_email_count=analyzed_email_count,
        high_priority_count=high_priority_count,
        need_reply_count=need_reply_count,
        meeting_request_count=meeting_request_count,
        task_count=task_count,
        pending_action_count=pending_action_count,
        today_event_count=today_event_count,
        calendar_suggestion_count=calendar_suggestion_count,
        draft_preview_count=draft_preview_count,
        trace_count=trace_count,
        category_breakdown=_breakdown(
            db,
            select(EmailAnalysis.category, func.count())
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id)
            .group_by(EmailAnalysis.category),
        ),
        priority_breakdown=_breakdown(
            db,
            select(EmailAnalysis.priority, func.count())
            .join(EmailRecord, EmailRecord.id == EmailAnalysis.email_id)
            .where(EmailRecord.user_id == user.id)
            .group_by(EmailAnalysis.priority),
        ),
        recent_emails=_recent_emails(db, user),
        recent_actions=_recent_actions(db, user),
        recent_traces=_recent_traces(db, user),
    )


def _breakdown(db: Session, statement) -> list[DashboardBreakdownItem]:
    """把 group by 查询结果转换为 Dashboard 图表数据。"""

    return [DashboardBreakdownItem(label=str(label), value=int(value)) for label, value in db.execute(statement).all()]


def _recent_emails(db: Session, user: User) -> list[DashboardRecentItem]:
    records = db.scalars(
        select(EmailRecord)
        .where(EmailRecord.user_id == user.id)
        .order_by(EmailRecord.received_at.desc().nullslast())
        .limit(5)
    ).all()
    return [
        DashboardRecentItem(
            id=item.id,
            title=item.subject,
            subtitle=item.sender,
            status=item.analysis.category if item.analysis else "unanalyzed",
            created_at=item.received_at.isoformat() if item.received_at else None,
        )
        for item in records
    ]


def _recent_actions(db: Session, user: User) -> list[DashboardRecentItem]:
    actions = db.scalars(
        select(PendingAction)
        .where(PendingAction.user_id == user.id)
        .order_by(PendingAction.created_at.desc())
        .limit(5)
    ).all()
    return [
        DashboardRecentItem(
            id=item.id,
            title=item.action_type,
            subtitle=item.risk_level,
            status=item.status,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )
        for item in actions
    ]


def _recent_traces(db: Session, user: User) -> list[DashboardRecentItem]:
    traces = db.scalars(
        select(AgentTrace)
        .where(AgentTrace.user_id == user.id)
        .order_by(AgentTrace.created_at.desc())
        .limit(5)
    ).all()
    return [
        DashboardRecentItem(
            id=item.id,
            title=item.task_type,
            subtitle=item.input_summary,
            status=item.status,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )
        for item in traces
    ]
