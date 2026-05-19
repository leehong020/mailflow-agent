"""第五阶段草稿审核与待确认操作 HTTP 接口。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.draft import (
    ConfirmActionResponse,
    CreatePendingActionForDraftResponse,
    CreateDraftPreviewRequest,
    CreateDraftPreviewResponse,
    DraftPreviewListResponse,
    DraftPreviewInfo,
    PendingActionInfo,
    PendingActionListResponse,
    RejectActionResponse,
    UpdateDraftPreviewRequest,
    UpdateDraftPreviewResponse,
)
from app.services.draft_service import DraftService
from app.services.email_analysis_service import EmailAnalysisService

router = APIRouter(prefix="/drafts", tags=["drafts"])


def _draft_info(preview) -> DraftPreviewInfo:
    """把 ORM 草稿预览转换为 API 响应。"""

    return DraftPreviewInfo(
        id=preview.id,
        source_email_id=preview.source_email_id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        tone=preview.tone,
        language=preview.language,
        status=preview.status,
        generation_reason=preview.generation_reason,
        created_at=preview.created_at.isoformat() if preview.created_at else None,
        updated_at=preview.updated_at.isoformat() if preview.updated_at else None,
    )


@router.get("/previews", response_model=DraftPreviewListResponse)
def list_draft_previews(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DraftPreviewListResponse:
    """Draft Review 页面使用的草稿列表。"""

    try:
        items, total = DraftService(db).list_previews(limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return DraftPreviewListResponse(items=[_draft_info(item) for item in items], total=total)


@router.get("/previews/{preview_id}", response_model=DraftPreviewInfo)
def get_draft_preview(preview_id: str, db: Session = Depends(get_db)) -> DraftPreviewInfo:
    """读取单个草稿预览。"""

    try:
        preview = DraftService(db).get_preview(preview_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="草稿不存在。")
    return _draft_info(preview)


@router.get("/emails/{email_id}/preview", response_model=DraftPreviewInfo | None)
def get_latest_preview(email_id: str, db: Session = Depends(get_db)):
    try:
        service = DraftService(db)
        preview = service.get_latest_preview(email_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if preview is None:
        return None
    return _draft_info(preview)


@router.post("/emails/{email_id}/preview", response_model=CreateDraftPreviewResponse)
def create_draft_preview(
    email_id: str,
    payload: CreateDraftPreviewRequest,
    db: Session = Depends(get_db),
) -> CreateDraftPreviewResponse:
    try:
        email = EmailAnalysisService(db).get_email_detail(email_id)
        if email is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮件不存在。")
        service = DraftService(db)
        preview = service.create_draft_preview(email=email, tone=payload.tone, language=payload.language)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CreateDraftPreviewResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        generation_reason=preview.generation_reason,
    )


@router.post("/previews/{preview_id}/pending", response_model=CreatePendingActionForDraftResponse)
def create_pending_action_for_preview(
    preview_id: str,
    db: Session = Depends(get_db),
) -> CreatePendingActionForDraftResponse:
    """用户审核草稿后，将草稿提交到 Pending Actions。"""

    try:
        service = DraftService(db)
        preview = service.get_preview(preview_id)
        if preview is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="草稿不存在。")
        action = service.create_pending_action_for_draft(draft_preview=preview)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CreatePendingActionForDraftResponse(
        action_id=action.id,
        status=action.status,
        message="已创建待确认操作，请到 Pending Actions 页面确认。",
    )


@router.put("/previews/{preview_id}", response_model=UpdateDraftPreviewResponse)
def update_draft_preview(
    preview_id: str,
    payload: UpdateDraftPreviewRequest,
    db: Session = Depends(get_db),
) -> UpdateDraftPreviewResponse:
    try:
        preview = DraftService(db).update_preview(
            preview_id,
            tone=payload.tone,
            language=payload.language,
            body=payload.body,
            subject=payload.subject,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return UpdateDraftPreviewResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        tone=preview.tone,
        language=preview.language,
        generation_reason=preview.generation_reason,
    )


@router.get("/pending", response_model=PendingActionListResponse)
def list_pending_actions(
    action_status: str | None = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> PendingActionListResponse:
    try:
        items, total = DraftService(db).list_pending_actions(status=action_status, limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return PendingActionListResponse(
        items=[
            PendingActionInfo(
                id=item.id,
                action_type=item.action_type,
                draft_preview_id=item.draft_preview_id,
                payload=json.loads(item.payload or "{}"),
                preview=json.loads(item.preview or "{}"),
                risk_level=item.risk_level,
                status=item.status,
                result=json.loads(item.result or "{}") if item.result else None,
                created_at=item.created_at.isoformat(),
                executed_at=item.executed_at.isoformat() if item.executed_at else None,
            )
            for item in items
        ],
        total=total,
    )


@router.post("/pending/{action_id}/confirm", response_model=ConfirmActionResponse)
def confirm_action(action_id: str, db: Session = Depends(get_db)) -> ConfirmActionResponse:
    try:
        result = DraftService(db).confirm_action(action_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ConfirmActionResponse(status="executed", result=result)


@router.post("/pending/{action_id}/reject", response_model=RejectActionResponse)
def reject_action(action_id: str, db: Session = Depends(get_db)) -> RejectActionResponse:
    try:
        DraftService(db).reject_action(action_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RejectActionResponse(status="rejected", message="已拒绝该待确认操作。")
