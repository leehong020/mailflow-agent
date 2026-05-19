"""邮件相关 HTTP 接口。

第二阶段只实现 Gmail 最近邮件列表。
第三阶段开始会在这里继续扩展邮件分析、详情页、草稿生成等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.email import EmailRecord
from app.schemas.email import (
    AnalyzeEmailsRequest,
    AnalyzeEmailsResponse,
    EmailAnalysisInfo,
    EmailDetailResponse,
    EmailListItem,
    EmailListResponse,
    ReanalyzeEmailResponse,
    TaskInfo,
)
from app.schemas.draft import CreateDraftPreviewRequest, CreateDraftPreviewResponse
from app.services.draft_service import DraftService
from app.services.email_analysis_service import EmailAnalysisService

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=EmailListResponse)
def list_emails(
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    need_reply: bool | None = Query(default=None),
    has_meeting_request: bool | None = Query(default=None),
    has_task: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EmailListResponse:
    """读取本地邮件列表，支持第三阶段看板筛选。"""

    try:
        service = EmailAnalysisService(db)
        records, total = service.list_emails(
            category=category,
            priority=priority,
            need_reply=need_reply,
            has_meeting_request=has_meeting_request,
            has_task=has_task,
            limit=limit,
            offset=offset,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return EmailListResponse(items=[_email_list_item(record) for record in records], total=total)


@router.post("/analyze", response_model=AnalyzeEmailsResponse)
def analyze_emails(
    payload: AnalyzeEmailsRequest,
    db: Session = Depends(get_db),
) -> AnalyzeEmailsResponse:
    """同步 Gmail 最近邮件，并只分析本地尚未分析的邮件。"""

    try:
        analyzed_count = EmailAnalysisService(db).analyze_unanalyzed_emails(limit=payload.limit)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AnalyzeEmailsResponse(
        status="completed",
        analyzed_count=analyzed_count,
        message=f"已完成 {analyzed_count} 封邮件的摘要、分类和任务提取。",
    )


@router.post("/{email_id}/reanalyze", response_model=ReanalyzeEmailResponse)
def reanalyze_email(email_id: str, db: Session = Depends(get_db)) -> ReanalyzeEmailResponse:
    """手动重新分析单封邮件。"""

    try:
        service = EmailAnalysisService(db)
        record = service.get_email_detail(email_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        service.reanalyze_email(record)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ReanalyzeEmailResponse(status="completed", message="已重新分析当前邮件。")


@router.post("/{email_id}/draft-reply", response_model=CreateDraftPreviewResponse)
def create_draft_reply(
    email_id: str,
    payload: CreateDraftPreviewRequest,
    db: Session = Depends(get_db),
) -> CreateDraftPreviewResponse:
    """开发文档 12.5 的草稿生成 API。

    该接口只生成 draft_preview，不直接创建 Gmail 草稿。
    用户需要进入 Draft Review 页面审核后，再创建 Pending Action。
    """

    try:
        email = EmailAnalysisService(db).get_email_detail(email_id)
        if email is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        preview = DraftService(db).create_draft_preview(email=email, tone=payload.tone, language=payload.language)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CreateDraftPreviewResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        generation_reason=preview.generation_reason,
    )


@router.get("/{email_id}", response_model=EmailDetailResponse)
def get_email_detail(email_id: str, db: Session = Depends(get_db)) -> EmailDetailResponse:
    """邮件详情页：返回原始邮件、Agent 分析结果和任务列表。"""

    try:
        record = EmailAnalysisService(db).get_email_detail(email_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")

    item = _email_list_item(record)
    return EmailDetailResponse(
        **item.model_dump(),
        body_text=record.body_text,
        tasks=[
            TaskInfo(
                id=task.id,
                title=task.title,
                description=task.description,
                deadline=task.deadline,
                priority=task.priority,
                status=task.status,
            )
            for task in record.tasks
        ],
    )


def _email_list_item(record: EmailRecord) -> EmailListItem:
    """把 ORM 邮件模型转换为 API 响应。"""

    analysis = None
    if record.analysis:
        analysis = EmailAnalysisInfo(
            summary=record.analysis.summary,
            key_points=record.analysis.key_points,
            category=record.analysis.category,
            priority=record.analysis.priority,
            need_reply=record.analysis.need_reply,
            has_task=record.analysis.has_task,
            has_meeting_request=record.analysis.has_meeting_request,
            reason=record.analysis.reason,
            recommended_actions=record.analysis.recommended_actions,
        )

    return EmailListItem(
        id=record.id,
        thread_id=record.thread_id,
        subject=record.subject,
        sender=record.sender,
        recipients=record.recipients,
        received_at=record.received_at.isoformat() if record.received_at else None,
        snippet=record.snippet,
        body_preview=(record.body_text or record.snippet)[:500] if (record.body_text or record.snippet) else None,
        analysis=analysis,
    )
