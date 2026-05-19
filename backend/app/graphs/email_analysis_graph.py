"""邮件分析工作流。

开发文档第 10.1 节定义的流程是：
Fetch Gmail Emails
    -> Email Summarizer Agent
    -> Email Triage Agent
    -> Task Extraction Agent
    -> Calendar Scheduler Agent
    -> Save Analysis Result
    -> Return to Vue Dashboard

第三阶段只实现前三个 Agent 和保存分析结果。
Calendar Scheduler Agent 属于后续日程阶段，因此这里不提前实现。
"""

from dataclasses import dataclass

from app.agents.email_summarizer_agent import EmailSummarizerAgent, EmailSummaryResult
from app.agents.email_triage_agent import EmailTriageAgent, EmailTriageResult
from app.agents.task_extraction_agent import ExtractedTask, TaskExtractionAgent
from app.models.email import EmailRecord


@dataclass(frozen=True)
class EmailAnalysisGraphResult:
    """邮件分析工作流输出。"""

    summary: EmailSummaryResult
    triage: EmailTriageResult
    tasks: list[ExtractedTask]


class EmailAnalysisGraph:
    """第三阶段邮件分析工作流编排器。"""

    def __init__(self) -> None:
        # 这里显式实例化文档中第三阶段要求的三个 Agent。
        # 后续接 LangGraph 真正图编排时，可以把这三个节点迁移为 graph node。
        self.summarizer = EmailSummarizerAgent()
        self.triage_agent = EmailTriageAgent()
        self.task_agent = TaskExtractionAgent()

    def run(self, email: EmailRecord) -> EmailAnalysisGraphResult:
        """按文档顺序执行摘要、分类、任务提取。"""

        # 执行顺序遵循开发文档第 10.1 节的邮件分析工作流。
        summary = self.summarizer.summarize(email)
        triage = self.triage_agent.triage(email)

        # 任务提取依赖分类 Agent 判断出的 has_task 和 priority。
        tasks = self.task_agent.extract(
            email=email,
            has_task=triage.has_task,
            priority=triage.priority,
        )
        return EmailAnalysisGraphResult(summary=summary, triage=triage, tasks=tasks)

    def get_prompts(self) -> dict[str, str]:
        """返回第三阶段 Agent 的系统提示词，便于排查和前端展示。"""

        return {
            "summarizer": self.summarizer.system_prompt,
            "triage": self.triage_agent.system_prompt,
            "task_extraction": self.task_agent.system_prompt,
        }
