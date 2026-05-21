"""第十三阶段写作记忆模型。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ComposeSession(Base):
    """写作会话，承载主动写邮件和回复邮件的短期记忆。"""

    __tablename__ = "compose_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    draft_preview_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    session_type: Mapped[str] = mapped_column(String(32), default="compose", index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    editor_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    messages: Mapped[list["ComposeMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ComposeMessage.created_at",
    )


class ComposeMessage(Base):
    """写作会话中的一条用户或 AI 消息。"""

    __tablename__ = "compose_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("compose_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), index=True)
    message_type: Mapped[str] = mapped_column(String(24), default="normal", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    editor_snapshot: Mapped[str] = mapped_column(Text, default="{}")
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ComposeSession] = relationship(back_populates="messages")
