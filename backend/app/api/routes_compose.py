"""第十二阶段主动写邮件 API。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.compose import ComposeDraftResponse, ComposeGenerateRequest, ComposeReviseRequest
from app.services.compose_service import ComposeService

router = APIRouter(prefix="/compose", tags=["compose"])


def _compose_response(preview, trace_id: str | None = None) -> ComposeDraftResponse:
    """把 DraftPreview 转成 Compose API 响应。"""

    return ComposeDraftResponse(
        draft_preview_id=preview.id,
        to=preview.to,
        subject=preview.subject,
        body=preview.body,
        tone=preview.tone,
        language=preview.language,
        generation_reason=preview.generation_reason,
        trace_id=trace_id,
    )


@router.post("/generate", response_model=ComposeDraftResponse)
def generate_compose_mail(
    payload: ComposeGenerateRequest,
    db: Session = Depends(get_db),
) -> ComposeDraftResponse:
    """根据用户写信目标生成主动写邮件草稿。"""

    try:
        preview, trace_id = ComposeService(db).generate_preview(
            goal=payload.goal,
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
            tone=payload.tone,
            language=payload.language,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _compose_response(preview, trace_id)


@router.post("/previews/{preview_id}/revise", response_model=ComposeDraftResponse)
def revise_compose_mail(
    preview_id: str,
    payload: ComposeReviseRequest,
    db: Session = Depends(get_db),
) -> ComposeDraftResponse:
    """根据用户对话要求修改主动写邮件草稿。"""

    try:
        preview, trace_id = ComposeService(db).revise_preview(
            preview_id,
            instruction=payload.instruction,
            to=payload.to,
            subject=payload.subject,
            body=payload.body,
            tone=payload.tone,
            language=payload.language,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _compose_response(preview, trace_id)
