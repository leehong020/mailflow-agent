"""Google Calendar 日程建议 LangGraph 工作流。

该图表达第六阶段的核心链路：
CalendarSchedulerAgent 解析会议请求 -> 查询 Google Calendar busy 时间 ->
计算可用时间段。

真正的 Google Credentials 恢复、CalendarSuggestion 写库和 Pending Action
创建仍由 CalendarService 完成。
"""

from datetime import datetime
from typing import Any, Callable, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]

from app.agents.calendar_scheduler_agent import CalendarScheduleRequest, CalendarSchedulerAgent
from app.models.email import EmailRecord

BusyQuery = Callable[[datetime, datetime], list[dict]]
SlotFinder = Callable[[datetime, datetime, list[dict], int, str], list[Any]]
WindowResolver = Callable[[CalendarScheduleRequest], tuple[datetime, datetime]]


class CalendarPlanningState(TypedDict, total=False):
    """日程建议图状态。"""

    email: EmailRecord
    duration_minutes: int
    plan: CalendarScheduleRequest
    window_start: datetime
    window_end: datetime
    busy_items: list[dict]
    slots: list[Any]
    query_busy: BusyQuery
    find_slots: SlotFinder
    resolve_window: WindowResolver


class CalendarPlanningGraph:
    """会议邮件到可用时间建议的工作流。"""

    def __init__(self) -> None:
        self.scheduler_agent = CalendarSchedulerAgent()
        self._compiled_graph = self._build_graph() if StateGraph is not None else None

    def run(
        self,
        *,
        email: EmailRecord,
        duration_minutes: int,
        resolve_window: WindowResolver,
        query_busy: BusyQuery,
        find_slots: SlotFinder,
    ) -> CalendarPlanningState:
        """执行日程建议图。"""

        state: CalendarPlanningState = {
            "email": email,
            "duration_minutes": duration_minutes,
            "resolve_window": resolve_window,
            "query_busy": query_busy,
            "find_slots": find_slots,
        }
        if self._compiled_graph is None:
            state = self._plan_node(state)
            state = self._query_busy_node(state)
            return self._find_slots_node(state)
        return self._compiled_graph.invoke(state)

    def _build_graph(self) -> Any:
        """构建 LangGraph 状态图。"""

        workflow = StateGraph(CalendarPlanningState)
        workflow.add_node("extract_meeting_request", self._plan_node)
        workflow.add_node("query_calendar_busy", self._query_busy_node)
        workflow.add_node("suggest_available_slots", self._find_slots_node)
        workflow.set_entry_point("extract_meeting_request")
        workflow.add_edge("extract_meeting_request", "query_calendar_busy")
        workflow.add_edge("query_calendar_busy", "suggest_available_slots")
        workflow.add_edge("suggest_available_slots", END)
        return workflow.compile()

    def _plan_node(self, state: CalendarPlanningState) -> CalendarPlanningState:
        """调用 CalendarSchedulerAgent 提取会议参数。"""

        plan = self.scheduler_agent.plan(
            email=state["email"],
            duration_minutes=state.get("duration_minutes", 30),
        )
        window_start, window_end = state["resolve_window"](plan)
        return {**state, "plan": plan, "window_start": window_start, "window_end": window_end}

    @staticmethod
    def _query_busy_node(state: CalendarPlanningState) -> CalendarPlanningState:
        """调用 Google Calendar freebusy 查询工具。"""

        busy_items = state["query_busy"](state["window_start"], state["window_end"])
        return {**state, "busy_items": busy_items}

    @staticmethod
    def _find_slots_node(state: CalendarPlanningState) -> CalendarPlanningState:
        """根据 busy 时间段计算推荐时间。"""

        plan = state["plan"]
        slots = state["find_slots"](
            state["window_start"],
            state["window_end"],
            state.get("busy_items", []),
            plan.duration_minutes,
            plan.timezone,
        )
        return {**state, "slots": slots}
