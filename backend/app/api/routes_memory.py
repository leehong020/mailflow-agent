"""第十三阶段写作记忆 API。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.memory import (
    ComposeMessageInfo,
    ComposeMessageRequest,
    ComposeSessionInfo,
    CreateComposeSessionRequest,
    UpdateComposeSessionRequest,
)
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/sessions", response_model=ComposeSessionInfo)
def create_session(payload: CreateComposeSessionRequest, db: Session = Depends(get_db)) -> ComposeSessionInfo:
    try:
        session = MemoryService(db).create_session(
            session_type=payload.session_type,
            title=payload.title,
            editor_snapshot=payload.editor_snapshot,
            draft_preview_id=payload.draft_preview_id,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return _session_info(session)


@router.get("/drafts/{draft_preview_id}/session", response_model=ComposeSessionInfo)
def get_or_create_draft_session(
    draft_preview_id: str,
    session_type: str = Query(default="compose"),
    db: Session = Depends(get_db),
) -> ComposeSessionInfo:
    """读取某个草稿对应的短期会话记忆，不存在则创建。"""

    try:
        session = MemoryService(db).get_or_create_session_for_draft(
            draft_preview_id=draft_preview_id,
            session_type=session_type,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_info(session)


@router.get("/sessions", response_model=list[ComposeSessionInfo])
def list_sessions(db: Session = Depends(get_db)) -> list[ComposeSessionInfo]:
    try:
        items, _ = MemoryService(db).list_sessions(limit=50, offset=0)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return [_session_info(item) for item in items]


@router.get("/sessions/{session_id}", response_model=ComposeSessionInfo)
def get_session(session_id: str, db: Session = Depends(get_db)) -> ComposeSessionInfo:
    try:
        session = MemoryService(db).get_session(session_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="写作会话不存在。")
    return _session_info(session)


@router.patch("/sessions/{session_id}", response_model=ComposeSessionInfo)
def update_session(session_id: str, payload: UpdateComposeSessionRequest, db: Session = Depends(get_db)) -> ComposeSessionInfo:
    try:
        session = MemoryService(db).update_session(session_id, title=payload.title, editor_snapshot=payload.editor_snapshot)
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _session_info(session)


@router.post("/sessions/{session_id}/messages", response_model=ComposeMessageInfo)
def add_message(session_id: str, payload: ComposeMessageRequest, db: Session = Depends(get_db)) -> ComposeMessageInfo:
    try:
        message = MemoryService(db).add_message(
            session_id,
            role=payload.role,
            content=payload.content,
            message_type=payload.message_type,
            editor_snapshot=payload.editor_snapshot,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _message_info(message)


@router.post("/drafts/{draft_preview_id}/messages", response_model=ComposeMessageInfo)
def add_draft_message(
    draft_preview_id: str,
    payload: ComposeMessageRequest,
    session_type: str = Query(default="compose"),
    db: Session = Depends(get_db),
) -> ComposeMessageInfo:
    """按草稿保存右侧 AI 对话消息。"""

    try:
        _, message = MemoryService(db).add_message_for_draft(
            draft_preview_id=draft_preview_id,
            session_type=session_type,
            role=payload.role,
            content=payload.content,
            editor_snapshot=payload.editor_snapshot,
        )
        db.commit()
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _message_info(message)


def _session_info(session) -> ComposeSessionInfo:
    service = MemoryService
    messages = [
        _message_dict(msg)
        for msg in getattr(session, "messages", [])
        if not getattr(msg, "archived", False)
    ]
    if getattr(session, "summary", ""):
        messages = [
            {
                "id": f"{session.id}:summary",
                "role": "system",
                "message_type": "summary",
                "content": session.summary,
                "editor_snapshot": {},
                "archived": False,
                "created_at": session.updated_at.isoformat(),
            },
            *messages,
        ]
    return ComposeSessionInfo(
        id=session.id,
        draft_preview_id=getattr(session, "draft_preview_id", ""),
        session_type=session.session_type,
        title=session.title,
        editor_snapshot=service._loads(session.editor_snapshot),
        summary=getattr(session, "summary", ""),
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        messages=messages,
    )


def _message_info(message) -> ComposeMessageInfo:
    data = _message_dict(message)
    return ComposeMessageInfo(**data)


def _message_dict(message) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "message_type": message.message_type,
        "content": message.content,
        "editor_snapshot": MemoryService._loads(message.editor_snapshot),
        "archived": message.archived,
        "created_at": message.created_at.isoformat(),
    }
