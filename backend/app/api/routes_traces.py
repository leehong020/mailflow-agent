"""Agent 轨迹 HTTP 接口。

第四阶段需要把多 Agent 工作流执行结果展示出来，
这里提供轨迹列表和详情接口，供前端时间线页面读取。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.trace import TraceInfo, TraceListItem, TraceListResponse, TraceEventInfo
from app.services.auth_service import AuthService
from app.services.trace_service import TraceService

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=TraceListResponse)
def list_traces(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TraceListResponse:
    try:
        user = AuthService(db).get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        traces, total = TraceService(db).list_traces(user=user, limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return TraceListResponse(
        items=[
            TraceListItem(
                id=trace.id,
                task_type=trace.task_type,
                status=trace.status,
                input_summary=trace.input_summary,
                output_summary=trace.output_summary,
                created_at=trace.created_at.isoformat(),
            )
            for trace in traces
        ],
        total=total,
    )


@router.get("/{trace_id}", response_model=TraceInfo)
def get_trace(trace_id: str, db: Session = Depends(get_db)) -> TraceInfo:
    try:
        user = AuthService(db).get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        trace = TraceService(db).get_trace(trace_id, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轨迹不存在。")

    return TraceInfo(
        id=trace.id,
        task_type=trace.task_type,
        status=trace.status,
        input_summary=trace.input_summary,
        output_summary=trace.output_summary,
        created_at=trace.created_at.isoformat(),
        completed_at=trace.completed_at.isoformat() if trace.completed_at else None,
        events=[
            TraceEventInfo(
                id=event.id,
                step=event.step,
                agent_name=event.agent_name,
                status=event.status,
                message=event.message,
                input_preview=event.input_preview,
                output_preview=event.output_preview,
                created_at=event.created_at.isoformat(),
            )
            for event in trace.events
        ],
    )


@router.get("/{trace_id}/stream")
def stream_trace(trace_id: str) -> dict:
    return {"trace_id": trace_id, "status": "not_implemented"}
