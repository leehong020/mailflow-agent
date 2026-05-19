"""第六阶段日程建议 ORM 模型。

calendar_suggestions 保存 Calendar Scheduler Agent 对会议邮件的分析结果：
- 会议标题；
- 参会人；
- 推荐时间段；
- 用户选择的时间段。

真正创建 Calendar Event 仍然通过 PendingAction 完成，保证高风险外部操作
必须由用户确认。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CalendarSuggestion(Base):
    """从会议邮件生成的日程建议。"""

    __tablename__ = "calendar_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    source_email_id: Mapped[str] = mapped_column(String(36), ForeignKey("email_records.id"), index=True)
    meeting_title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(Text, default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    duration_minutes: Mapped[int] = mapped_column(default=30)
    participants: Mapped[list[str]] = mapped_column(JSON, default=list)
    suggested_slots: Mapped[list[dict]] = mapped_column(JSON, default=list)
    selected_slot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="suggested", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    email = relationship("EmailRecord")
