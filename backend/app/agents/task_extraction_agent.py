"""Task Extraction Agent。

该 Agent 从邮件中抽取任务看板需要的待办事项。主路径由大模型完成语义
抽取，代码负责输出校验和数据库可保存格式转换。
"""

from dataclasses import dataclass

from app.agents.base import BaseLLMAgent
from app.models.email import EmailRecord
from app.schemas.llm_outputs import TaskExtractionLLMOutput


@dataclass(frozen=True)
class ExtractedTask:
    """任务提取 Agent 的结构化输出。"""

    title: str
    description: str
    deadline: str | None
    priority: str


class TaskExtractionAgent(BaseLLMAgent):
    """待办事项提取 Agent。"""

    name = "TaskExtractionAgent"
    prompt_file = "task_extraction_agent.txt"
    allowed_priorities = {"high", "medium", "low"}

    def extract(self, email: EmailRecord, has_task: bool, priority: str) -> list[ExtractedTask]:
        """从邮件中提取任务。

        如果分类 Agent 未识别出任务，则直接返回空列表。
        """

        content = self.compact_text(" ".join([email.subject, email.snippet, email.body_text]))
        if not content:
            return []

        try:
            tasks = self._extract_with_llm(email=email, has_task=has_task, priority=priority)
        except Exception as exc:
            tasks = self._fallback_tasks(email=email, has_task=has_task, priority=priority, error=exc)

        return tasks

    def _extract_with_llm(self, *, email: EmailRecord, has_task: bool, priority: str) -> list[ExtractedTask]:
        """调用大模型提取待办事项。"""

        data = self.run_json(
            user_prompt=(
                "请从下面这封邮件中提取可以进入任务看板的待办事项。\n"
                f"上游分类 Agent 是否判断存在任务：{has_task}\n"
                f"上游分类 Agent 给出的邮件优先级：{priority}\n\n"
                f"{self.build_email_context(email)}"
            ),
        )
        output = self.validate_llm_output(TaskExtractionLLMOutput, data)
        tasks: list[ExtractedTask] = []
        for item in output.tasks:
            tasks.append(
                ExtractedTask(
                    title=item.title,
                    description=item.description or item.title,
                    deadline=item.deadline,
                    priority=item.priority,
                )
            )
        return tasks

    def _fallback_tasks(
        self,
        *,
        email: EmailRecord,
        has_task: bool,
        priority: str,
        error: Exception | None = None,
    ) -> list[ExtractedTask]:
        """模型不可用时的保守兜底任务。

        如果上游分类 Agent 已经明确判断有任务，则创建一个人工核查任务；
        否则返回空列表，避免误把普通邮件写进任务看板。
        """

        if not has_task:
            return []
        task_priority = priority if priority in self.allowed_priorities else "medium"
        description = "模型输出校验或调用失败，上游分类认为该邮件可能包含待办，请人工查看邮件详情确认。"
        if error:
            description = f"{description}原因：{self.error_summary(error)}"
        return [
            ExtractedTask(
                title=f"核查邮件待办：{email.subject or '(无主题)'}"[:120],
                description=description,
                deadline=None,
                priority=task_priority,
            )
        ]
