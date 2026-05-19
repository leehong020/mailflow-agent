"""第五阶段草稿审核与待确认操作 ORM 模型。

开发文档第 11.7、11.8 节要求：
1. Draft Review 页面展示 Agent 生成的回复草稿；
2. Pending Actions 页面集中管理需要用户确认的外部操作；
3. 确认后才真正创建 Gmail 草稿。

为了保持课程项目可控，第一版只实现 Gmail 草稿相关模型，
后续如果接入 Calendar 同样可以沿用 PendingAction 设计。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DraftPreview(Base):
    """回复草稿预览。"""

    __tablename__ = "draft_previews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    source_email_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_records.id"), index=True)
    to: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(32), default="polite")
    language: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[str] = mapped_column(String(32), default="preview", index=True)
    generation_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    email = relationship("EmailRecord")
    pending_action = relationship("PendingAction", back_populates="draft_preview", uselist=False)


class PendingAction(Base):
    """需要用户确认后才能执行的高风险操作。"""

    __tablename__ = "pending_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    draft_preview_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("draft_previews.id"), nullable=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    preview: Mapped[str] = mapped_column(Text, default="{}")
    risk_level: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    result: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    draft_preview = relationship("DraftPreview", back_populates="pending_action")
