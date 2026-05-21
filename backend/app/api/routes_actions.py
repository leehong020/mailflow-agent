"""第七阶段 Human-in-the-loop 操作中心 HTTP 接口。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.action import ActionInfo, ActionListResponse, ConfirmActionResponse, RejectActionResponse
from app.services.action_service import ActionService

router = APIRouter(prefix="/actions", tags=["actions"])


def _action_info(action) -> ActionInfo:
    """把 PendingAction ORM 转换为 API 响应。"""

    return ActionInfo(
        id=action.id,
        action_type=action.action_type,
        draft_preview_id=action.draft_preview_id,
        payload=json.loads(action.payload or "{}"),
        preview=json.loads(action.preview or "{}"),
        risk_level=action.risk_level,
        status=action.status,
        result=json.loads(action.result or "{}") if action.result else None,
        created_at=action.created_at.isoformat(),
        executed_at=action.executed_at.isoformat() if action.executed_at else None,
    )


@router.get("", response_model=ActionListResponse)
def list_actions(
    action_status: str | None = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ActionListResponse:
    """Pending Actions 页面读取统一操作列表。"""

    try:
        items, total = ActionService(db).list_actions(status=action_status, limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return ActionListResponse(items=[_action_info(item) for item in items], total=total)


@router.post("/{action_id}/confirm", response_model=ConfirmActionResponse)
def confirm_action(action_id: str, db: Session = Depends(get_db)) -> ConfirmActionResponse:
    """用户确认后执行外部操作。"""

    try:
        result = ActionService(db).confirm_action(action_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ConfirmActionResponse(status="executed", result=result)


@router.post("/{action_id}/reject", response_model=RejectActionResponse)
def reject_action(action_id: str, db: Session = Depends(get_db)) -> RejectActionResponse:
    """用户拒绝外部操作。"""

    try:
        ActionService(db).reject_action(action_id)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RejectActionResponse(status="rejected", message="已拒绝该待确认操作。")
