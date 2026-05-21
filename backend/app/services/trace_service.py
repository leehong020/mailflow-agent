"""Agent 轨迹记录服务。

第四阶段的核心目标是把多 Agent 工作流执行过程保存下来，
这样前端就可以通过列表页和时间线页展示：
1. 当前任务的总体状态；
2. 每个 Agent 的输入输出摘要；
3. 失败原因和执行顺序。

为了保持课程项目易维护，这里不引入过重的消息队列，
而是直接用数据库持久化轨迹数据。
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.trace import AgentTrace, AgentTraceEvent
from app.models.user import User


class TraceService:
    """轨迹业务服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trace(
        self,
        *,
        user: User,
        task_type: str,
        input_summary: str = "",
    ) -> AgentTrace:
        """创建一条新的轨迹记录。"""

        trace = AgentTrace(user_id=user.id, task_type=task_type, input_summary=input_summary)
        self.db.add(trace)
        self.db.flush()
        return trace

    def add_event(
        self,
        *,
        trace: AgentTrace,
        step: int,
        agent_name: str,
        status: str,
        message: str,
        input_preview: str = "",
        output_preview: str = "",
    ) -> AgentTraceEvent:
        """给当前轨迹追加一条步骤事件。"""

        event = AgentTraceEvent(
            trace_id=trace.id,
            step=step,
            agent_name=agent_name,
            status=status,
            message=message,
            input_preview=input_preview,
            output_preview=output_preview,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def complete_trace(self, trace: AgentTrace, *, status: str = "completed", output_summary: str = "") -> AgentTrace:
        """标记轨迹执行完成。"""

        trace.status = status
        trace.output_summary = output_summary
        trace.completed_at = datetime.now(timezone.utc)
        self.db.flush()
        return trace

    def fail_trace(self, trace: AgentTrace, *, output_summary: str = "") -> AgentTrace:
        """标记轨迹执行失败。"""

        return self.complete_trace(trace, status="failed", output_summary=output_summary)

    def list_traces(
        self,
        *,
        user: User,
        status: str | None = None,
        task_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AgentTrace], int]:
        """分页查询轨迹列表。"""

        query = (
            select(AgentTrace)
            .options(joinedload(AgentTrace.events))
            .where(AgentTrace.user_id == user.id)
        )
        if status:
            query = query.where(AgentTrace.status == status)
        if task_type:
            query = query.where(AgentTrace.task_type == task_type)
        query = query.order_by(AgentTrace.created_at.desc())
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        traces = self.db.scalars(query.offset(offset).limit(limit)).unique().all()
        return list(traces), total

    def get_trace(self, trace_id: str, *, user: User) -> AgentTrace | None:
        """查询单条轨迹详情。"""

        return self.db.scalars(
            select(AgentTrace)
            .options(joinedload(AgentTrace.events))
            .where(AgentTrace.id == trace_id, AgentTrace.user_id == user.id)
        ).unique().first()
