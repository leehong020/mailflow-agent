"""Agent 轨迹 HTTP 接口。

第四阶段需要把多 Agent 工作流执行结果展示出来，
这里提供轨迹列表和详情接口，供前端时间线页面读取。
"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.trace import TraceInfo, TraceListItem, TraceListResponse, TraceEventInfo
from app.services.auth_service import AuthService
from app.services.trace_service import TraceService

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=TraceListResponse)
def list_traces(
    trace_status: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TraceListResponse:
    try:
        user = AuthService(db).get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        traces, total = TraceService(db).list_traces(
            user=user,
            status=trace_status,
            task_type=task_type,
            limit=limit,
            offset=offset,
        )
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
                duration_ms=_duration_ms(trace.created_at, trace.completed_at),
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
        duration_ms=_duration_ms(trace.created_at, trace.completed_at),
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
def stream_trace(trace_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """通过 SSE 推送单条 Trace 的事件。

    前端打开 EventSource 后，这里会先推送已有历史事件，随后每秒轮询一次
    数据库，把新增事件继续推给前端。当前分析流程仍然是同步请求，但节点在
    执行中会 flush trace event，所以另一个浏览器页可以实时看到进度。
    """

    user = AuthService(db).get_current_user()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="尚未连接 Google 账号。")
    if TraceService(db).get_trace(trace_id, user=user) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="轨迹不存在。")

    def event_stream():
        sent_event_ids: set[str] = set()
        idle_rounds = 0
        while idle_rounds < 600:
            trace = TraceService(db).get_trace(trace_id, user=user)
            if trace is None:
                yield _sse("error", {"message": "轨迹不存在。"})
                return

            for event in trace.events:
                if event.id in sent_event_ids:
                    continue
                sent_event_ids.add(event.id)
                yield _sse(
                    "trace_event",
                    {
                        "id": event.id,
                        "step": event.step,
                        "agent_name": event.agent_name,
                        "status": event.status,
                        "message": event.message,
                        "input_preview": event.input_preview,
                        "output_preview": event.output_preview,
                        "created_at": event.created_at.isoformat(),
                    },
                )

            yield _sse(
                "trace_status",
                {
                    "id": trace.id,
                    "status": trace.status,
                    "output_summary": trace.output_summary,
                    "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
                    "duration_ms": _duration_ms(trace.created_at, trace.completed_at),
                },
            )
            if trace.status in {"completed", "failed"}:
                return
            idle_rounds += 1
            time.sleep(1)

        yield _sse("timeout", {"message": "轨迹流已超时，请刷新页面重新订阅。"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _duration_ms(start, end) -> int | None:
    """计算轨迹耗时毫秒。"""

    if not start or not end:
        return None
    return int((end - start).total_seconds() * 1000)


def _sse(event: str, data: dict) -> str:
    """把字典编码成标准 SSE 文本帧。"""

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
