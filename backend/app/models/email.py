"""邮件与第三阶段分析结果模型。

第三阶段新增三类核心数据：
1. EmailRecord：从 Gmail 同步下来的原始邮件；
2. EmailAnalysis：Agent 对邮件的摘要、分类、优先级判断；
3. TaskItem：Task Extraction Agent 从邮件中识别出的待办事项。

这些表会被 Dashboard、Inbox 看板、邮件详情页复用。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EmailRecord(Base):
    """本地邮件记录表。

    只保存项目需要展示和分析的字段，不保存附件原文。
    gmail_message_id 使用唯一约束，避免重复同步同一封邮件。
    """

    __tablename__ = "email_records"
    __table_args__ = (UniqueConstraint("user_id", "gmail_message_id", name="uq_user_gmail_message"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    gmail_message_id: Mapped[str] = mapped_column(String(128), index=True)
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subject: Mapped[str] = mapped_column(Text, default="(无主题)")
    sender: Mapped[str] = mapped_column(Text, default="")
    recipients: Mapped[list[str]] = mapped_column(JSON, default=list)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    analysis: Mapped["EmailAnalysis | None"] = relationship(
        back_populates="email",
        cascade="all, delete-orphan",
        uselist=False,
    )
    tasks: Mapped[list["TaskItem"]] = relationship(back_populates="email", cascade="all, delete-orphan")


class EmailAnalysis(Base):
    """邮件分析结果表，对应开发文档中的 email_analysis。"""

    __tablename__ = "email_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_records.id"), unique=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(64), default="notification", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="low", index=True)
    need_reply: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_task: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_meeting_request: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    recommended_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    email: Mapped[EmailRecord] = relationship(back_populates="analysis")


class TaskItem(Base):
    """从邮件中提取出的待办事项。"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    source_email_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_records.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="todo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    email: Mapped[EmailRecord] = relationship(back_populates="tasks")
