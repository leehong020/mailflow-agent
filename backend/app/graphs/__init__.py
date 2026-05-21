"""MailFlow Agent 的 LangGraph 工作流入口。

这里只导出真正具备多节点编排价值的工作流。单 Agent 调用、简单安全规则和
普通数据库事务保留在 Service 层，避免为了框架而过度图化。
"""

from app.graphs.calendar_planning_graph import CalendarPlanningGraph
from app.graphs.email_analysis_graph import EmailAnalysisGraph

__all__ = [
    "CalendarPlanningGraph",
    "EmailAnalysisGraph",
]
