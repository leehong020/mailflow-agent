"""Agent 执行轨迹相关 ORM 模型。

第四阶段的目标是把多 Agent 执行过程持久化下来，
让前端可以按时间线查看：
1. 一个任务的整体执行记录；
2. 每个 Agent 节点的开始、结束和错误信息；
3. 每一步执行时展示给用户的摘要文本。

这里的设计尽量保持简单，便于课程项目稳定演示。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentTrace(Base):
    """单次 Agent 工作流执行记录。"""

    __tablename__ = "agent_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["AgentTraceEvent"]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
        order_by="AgentTraceEvent.step",
    )


class AgentTraceEvent(Base):
    """单次轨迹中的步骤事件。"""

    __tablename__ = "agent_trace_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    trace_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_traces.id"), index=True)
    step: Mapped[int] = mapped_column(Integer, default=1)
    agent_name: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    input_preview: Mapped[str] = mapped_column(Text, default="")
    output_preview: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trace: Mapped[AgentTrace] = relationship(back_populates="events")
