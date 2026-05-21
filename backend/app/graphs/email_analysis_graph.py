"""邮件分析 LangGraph 工作流。

开发文档要求项目基于 LangGraph 展示多 Agent 工作流，因此这里不再使用
普通的顺序函数调用，而是把第三阶段的三个 Agent 建成明确的图节点：

EmailSummarizerAgent -> EmailTriageAgent -> TaskExtractionAgent

CalendarSchedulerAgent 属于第六阶段的日程规划链路，不放进基础邮件分析图。
图节点仍然保持同步执行，便于和当前 FastAPI 请求模型、SQLite 本地演示保持
一致；后续如果要改成后台任务，只需要把调用入口迁移到任务队列即可。
"""

from dataclasses import dataclass
from typing import Any, Callable, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - 本地未安装依赖时提供清晰降级。
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]

from app.agents.email_summarizer_agent import EmailSummarizerAgent, EmailSummaryResult
from app.agents.email_triage_agent import EmailTriageAgent, EmailTriageResult
from app.agents.task_extraction_agent import ExtractedTask, TaskExtractionAgent
from app.models.email import EmailRecord

TraceCallback = Callable[[int, str, str, str, str, str], None]


@dataclass(frozen=True)
class EmailAnalysisGraphResult:
    """邮件分析工作流输出。"""

    summary: EmailSummaryResult
    triage: EmailTriageResult
    tasks: list[ExtractedTask]


class EmailAnalysisState(TypedDict, total=False):
    """LangGraph 节点之间传递的状态。

    LangGraph 的状态必须是可合并的字典结构。这里把邮件对象、各 Agent 输出
    和可选的 trace 回调都放进状态里，节点执行完成后补充自己的输出字段。
    """

    email: EmailRecord
    summary: EmailSummaryResult
    triage: EmailTriageResult
    tasks: list[ExtractedTask]
    on_event: TraceCallback | None


class EmailAnalysisGraph:
    """第三阶段邮件分析工作流编排器。

    该类真正使用 LangGraph 构建图。为了降低本地环境的安装门槛，如果当前
    venv 尚未安装 langgraph，会退回到同样顺序的线性执行，并且 requirements
    已经声明依赖，安装后即可自动使用 LangGraph。
    """

    def __init__(self) -> None:
        self.summarizer = EmailSummarizerAgent()
        self.triage_agent = EmailTriageAgent()
        self.task_agent = TaskExtractionAgent()
        self._compiled_graph = self._build_graph() if StateGraph is not None else None

    def run(self, email: EmailRecord, on_event: TraceCallback | None = None) -> EmailAnalysisGraphResult:
        """执行邮件分析图。

        on_event 用于把每个节点的 running/completed 状态写入 Agent Trace。
        FastAPI 仍然是同步请求，但 Trace SSE 会轮询这些数据库事件并推送给前端。
        """

        initial_state: EmailAnalysisState = {"email": email, "on_event": on_event}
        if self._compiled_graph is None:
            final_state = self._run_linear(initial_state)
        else:
            final_state = self._compiled_graph.invoke(initial_state)

        return EmailAnalysisGraphResult(
            summary=final_state["summary"],
            triage=final_state["triage"],
            tasks=final_state["tasks"],
        )

    def get_prompts(self) -> dict[str, str]:
        """返回第三阶段 Agent 的系统提示词，便于排查和前端展示。"""

        return {
            "summarizer": self.summarizer.system_prompt,
            "triage": self.triage_agent.system_prompt,
            "task_extraction": self.task_agent.system_prompt,
        }

    def _build_graph(self) -> Any:
        """构建 LangGraph 状态图。"""

        workflow = StateGraph(EmailAnalysisState)
        workflow.add_node("summarize", self._summarize_node)
        workflow.add_node("triage", self._triage_node)
        workflow.add_node("extract_tasks", self._task_node)
        workflow.set_entry_point("summarize")
        workflow.add_edge("summarize", "triage")
        workflow.add_edge("triage", "extract_tasks")
        workflow.add_edge("extract_tasks", END)
        return workflow.compile()

    def _run_linear(self, state: EmailAnalysisState) -> EmailAnalysisState:
        """缺少 langgraph 包时的降级执行。

        这不是目标运行模式，只是为了让代码在依赖尚未安装时能给出可用结果。
        正式环境请执行 `pip install -r backend/requirements.txt`。
        """

        state = self._summarize_node(state)
        state = self._triage_node(state)
        return self._task_node(state)

    def _summarize_node(self, state: EmailAnalysisState) -> EmailAnalysisState:
        """LangGraph 节点：生成邮件摘要。"""

        email = state["email"]
        self._emit(state, 1, "EmailSummarizerAgent", "running", "开始生成邮件摘要。", email.subject or "", "")
        summary = self.summarizer.summarize(email)
        self._emit(state, 1, "EmailSummarizerAgent", "completed", "邮件摘要生成完成。", "", summary.summary)
        return {**state, "summary": summary}

    def _triage_node(self, state: EmailAnalysisState) -> EmailAnalysisState:
        """LangGraph 节点：判断分类、优先级和推荐动作。"""

        email = state["email"]
        self._emit(state, 2, "EmailTriageAgent", "running", "开始判断邮件分类与优先级。", email.subject or "", "")
        triage = self.triage_agent.triage(email)
        self._emit(
            state,
            2,
            "EmailTriageAgent",
            "completed",
            "邮件分类完成。",
            "",
            f"{triage.category} / {triage.priority}",
        )
        return {**state, "triage": triage}

    def _task_node(self, state: EmailAnalysisState) -> EmailAnalysisState:
        """LangGraph 节点：根据 triage 结果提取待办事项。"""

        email = state["email"]
        triage = state["triage"]
        self._emit(state, 3, "TaskExtractionAgent", "running", "开始提取待办事项。", email.subject or "", "")
        tasks = self.task_agent.extract(email=email, has_task=triage.has_task, priority=triage.priority)
        self._emit(
            state,
            3,
            "TaskExtractionAgent",
            "completed",
            "待办事项提取完成。",
            "",
            f"提取到 {len(tasks)} 个任务。",
        )
        return {**state, "tasks": tasks}

    @staticmethod
    def _emit(
        state: EmailAnalysisState,
        step: int,
        agent_name: str,
        status: str,
        message: str,
        input_preview: str,
        output_preview: str,
    ) -> None:
        """向 TraceService 回调写入节点状态。"""

        callback = state.get("on_event")
        if callback:
            callback(step, agent_name, status, message, input_preview[:120], output_preview[:200])
