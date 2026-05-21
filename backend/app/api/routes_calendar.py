"""第六阶段 Google Calendar HTTP 接口。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.calendar import (
    CalendarEventInfo,
    CalendarEventsResponse,
    CalendarEventMutationRequest,
    CalendarSlotInfo,
    CalendarSuggestionInfo,
    CreateCalendarPendingActionRequest,
    CreateCalendarPendingActionResponse,
    DeleteCalendarEventPendingRequest,
    SuggestSlotsRequest,
    SuggestSlotsResponse,
)
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _slot_info(raw: dict) -> CalendarSlotInfo:
    """把数据库中的推荐时间段转换成 API 响应。"""

    return CalendarSlotInfo(
        start=str(raw.get("start") or ""),
        end=str(raw.get("end") or ""),
        reason=str(raw.get("reason") or ""),
    )


def _suggestion_info(suggestion) -> CalendarSuggestionInfo:
    """把 CalendarSuggestion ORM 转换为前端结构。"""

    return CalendarSuggestionInfo(
        id=suggestion.id,
        source_email_id=suggestion.source_email_id,
        meeting_title=suggestion.meeting_title,
        description=suggestion.description,
        location=suggestion.location,
        timezone=suggestion.timezone,
        duration_minutes=suggestion.duration_minutes,
        participants=suggestion.participants or [],
        suggested_slots=[_slot_info(item) for item in suggestion.suggested_slots or []],
        selected_slot=_slot_info(suggestion.selected_slot) if suggestion.selected_slot else None,
        status=suggestion.status,
        created_at=suggestion.created_at.isoformat() if suggestion.created_at else None,
    )


@router.get("/events", response_model=CalendarEventsResponse)
def list_calendar_events(
    range_name: str = Query(default="today", alias="range", pattern="^(today|week)$"),
    db: Session = Depends(get_db),
) -> CalendarEventsResponse:
    """读取 Google Calendar 今日或本周日程。"""

    try:
        items, total = CalendarService(db).list_events(range_name=range_name)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CalendarEventsResponse(items=[CalendarEventInfo(**item) for item in items], total=total)


@router.post("/events/pending", response_model=CreateCalendarPendingActionResponse)
def create_manual_calendar_event_pending(
    payload: CalendarEventMutationRequest,
    db: Session = Depends(get_db),
) -> CreateCalendarPendingActionResponse:
    """手动创建 Calendar Event，并先放入 Pending Actions。"""

    try:
        action = CalendarService(db).create_manual_event_action(**payload.model_dump())
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateCalendarPendingActionResponse(
        action_id=action.id,
        status=action.status,
        message="已创建新增日程的待确认操作，请到 Pending Actions 页面确认。",
    )


@router.get("/events/{event_id}", response_model=CalendarEventInfo)
def get_calendar_event_detail(event_id: str, db: Session = Depends(get_db)) -> CalendarEventInfo:
    """Calendar Event Detail 页面读取单个日程详情。"""

    try:
        item = CalendarService(db).get_event(event_id=event_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CalendarEventInfo(**item)


@router.post("/events/{event_id}/update-pending", response_model=CreateCalendarPendingActionResponse)
def create_update_calendar_event_pending(
    event_id: str,
    payload: CalendarEventMutationRequest,
    db: Session = Depends(get_db),
) -> CreateCalendarPendingActionResponse:
    """修改 Calendar Event，并在进入 Pending Actions 前完成冲突检测。"""

    try:
        action = CalendarService(db).create_update_event_action(event_id=event_id, **payload.model_dump())
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateCalendarPendingActionResponse(
        action_id=action.id,
        status=action.status,
        message="已创建修改日程的待确认操作，请到 Pending Actions 页面确认。",
    )


@router.post("/events/{event_id}/delete-pending", response_model=CreateCalendarPendingActionResponse)
def create_delete_calendar_event_pending(
    event_id: str,
    payload: DeleteCalendarEventPendingRequest,
    db: Session = Depends(get_db),
) -> CreateCalendarPendingActionResponse:
    """删除 Calendar Event，并先放入 Pending Actions。"""

    try:
        action = CalendarService(db).create_delete_event_action(event_id=event_id, reason=payload.reason)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateCalendarPendingActionResponse(
        action_id=action.id,
        status=action.status,
        message="已创建删除日程的待确认操作，请到 Pending Actions 页面确认。",
    )


@router.get("/suggestions", response_model=list[CalendarSuggestionInfo])
def list_calendar_suggestions(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[CalendarSuggestionInfo]:
    """Calendar Planner 页面加载历史日程建议。"""

    try:
        items, _ = CalendarService(db).list_suggestions(limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return [_suggestion_info(item) for item in items]


@router.post("/suggest-slots", response_model=SuggestSlotsResponse)
def suggest_slots(payload: SuggestSlotsRequest, db: Session = Depends(get_db)) -> SuggestSlotsResponse:
    """根据会议邮件查询日历并生成可用时间段。"""

    try:
        suggestion = CalendarService(db).suggest_slots(
            email_id=payload.email_id,
            duration_minutes=payload.duration_minutes,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SuggestSlotsResponse(suggestion=_suggestion_info(suggestion))


@router.post("/suggestions/{suggestion_id}/pending", response_model=CreateCalendarPendingActionResponse)
def create_calendar_pending_action(
    suggestion_id: str,
    payload: CreateCalendarPendingActionRequest,
    db: Session = Depends(get_db),
) -> CreateCalendarPendingActionResponse:
    """用户选择推荐时间段后，创建待确认 Calendar Event 操作。"""

    try:
        service = CalendarService(db)
        suggestion = service.get_suggestion(suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日程建议不存在。")
        action = service.create_pending_action(
            suggestion=suggestion,
            selected_slot=payload.selected_slot.model_dump(),
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreateCalendarPendingActionResponse(
        action_id=action.id,
        status=action.status,
        message="已创建待确认日程操作，请到 Pending Actions 页面确认。",
    )
