"""Task Extraction Agent。

职责来自开发文档第 9.6 节：
- 从邮件中提取待办事项；
- 识别任务截止时间；
- 判断任务优先级；
- 将任务保存到数据库；
- 在前端任务面板中展示。
"""

import re
from dataclasses import dataclass

from app.core.llm import LLMClient
from app.models.email import EmailRecord
from app.prompts import TASK_EXTRACTION_SYSTEM_PROMPT


@dataclass(frozen=True)
class ExtractedTask:
    """任务提取 Agent 的结构化输出。"""

    title: str
    description: str
    deadline: str | None
    priority: str


class TaskExtractionAgent:
    """待办事项提取 Agent。"""

    name = "TaskExtractionAgent"
    system_prompt = TASK_EXTRACTION_SYSTEM_PROMPT

    task_patterns = [
        r"(?:please|kindly)\s+(?P<task>.{8,120})",
        r"(?:todo|task|action item)[:：]\s*(?P<task>.{4,120})",
        r"(?:请|麻烦|需要)(?P<task>.{4,80})",
    ]
    deadline_patterns = [
        r"\b(?:by|before|due)\s+(?P<deadline>[A-Za-z]+\s+\d{1,2}|\d{4}-\d{1,2}-\d{1,2}|tomorrow|today)\b",
        r"(?P<deadline>今天|明天|本周|下周|周一|周二|周三|周四|周五|周六|周日|星期一|星期二|星期三|星期四|星期五|星期六|星期日)",
    ]

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def extract(self, email: EmailRecord, has_task: bool, priority: str) -> list[ExtractedTask]:
        """从邮件中提取任务。

        如果分类 Agent 未识别出任务，则直接返回空列表。
        """

        content = " ".join([email.subject, email.snippet, email.body_text]).strip()
        normalized = " ".join(content.split())
        if not normalized:
            return []

        try:
            tasks = self._extract_with_llm(email=email, content=normalized, priority=priority)
        except Exception:
            tasks = self._extract_with_rules(email=email, content=normalized, priority=priority)

        if tasks:
            return tasks
        if has_task:
            return self._extract_with_rules(email=email, content=normalized, priority=priority)
        return []

    def _extract_with_llm(self, *, email: EmailRecord, content: str, priority: str) -> list[ExtractedTask]:
        """调用大模型提取待办事项。"""

        client = self.llm_client or LLMClient()
        data = client.complete_json(
            system_prompt=self.system_prompt,
            user_prompt=(
                f"邮件主题：{email.subject}\n"
                f"发件人：{email.sender}\n"
                f"邮件内容：\n{content[:6000]}\n\n"
                "请提取其中明确的待办任务。"
            ),
        )
        raw_tasks = data.get("tasks") or []
        if not isinstance(raw_tasks, list):
            return []

        tasks: list[ExtractedTask] = []
        for item in raw_tasks[:5]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            task_priority = str(item.get("priority") or priority)
            if task_priority not in {"high", "medium", "low"}:
                task_priority = priority if priority in {"high", "medium", "low"} else "medium"
            deadline = item.get("deadline")
            tasks.append(
                ExtractedTask(
                    title=title[:120],
                    description=str(item.get("description") or content[:300]).strip()[:500],
                    deadline=str(deadline).strip() if deadline else None,
                    priority=task_priority,
                )
            )
        return tasks

    def _extract_with_rules(self, *, email: EmailRecord, content: str, priority: str) -> list[ExtractedTask]:
        """规则兜底任务提取。"""

        deadline = self._extract_deadline(content)
        task_title = self._extract_title(content) or email.subject or "处理邮件中的待办事项"

        return [
            ExtractedTask(
                title=task_title[:120],
                description=content[:300],
                deadline=deadline,
                priority=priority if priority in {"high", "medium", "low"} else "medium",
            )
        ]

    def _extract_title(self, content: str) -> str | None:
        """优先从明确的任务表达中提取任务标题。"""

        for pattern in self.task_patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                return match.group("task").strip(" .。；;")
        return None

    def _extract_deadline(self, content: str) -> str | None:
        """提取自然语言截止时间文本，后续可替换为更强的时间解析器。"""

        for pattern in self.deadline_patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                return match.group("deadline")
        return None
