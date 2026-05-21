"""第十三阶段写作记忆服务。"""

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.agents.memory_agent import MemoryAgent
from app.models.compose import ComposeMessage, ComposeSession
from app.models.draft import DraftPreview
from app.models.user import User
from app.services.auth_service import AuthService


class MemoryService:
    """管理写作工作台的短期会话记忆。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth_service = AuthService(db)
        self.memory_agent = MemoryAgent()
        self.max_visible_messages = 30
        self.max_visible_chars = 12000
        self.keep_recent_messages = 10

    def create_session(
        self,
        *,
        session_type: str,
        title: str = "",
        editor_snapshot: dict | None = None,
        draft_preview_id: str = "",
    ) -> ComposeSession:
        user = self._current_user()
        session = ComposeSession(
            user_id=user.id,
            draft_preview_id=draft_preview_id,
            session_type=session_type,
            title=title,
            editor_snapshot=self._dump(editor_snapshot or {}),
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_or_create_session_for_draft(
        self,
        *,
        draft_preview_id: str,
        session_type: str,
        title: str = "",
        editor_snapshot: dict | None = None,
    ) -> ComposeSession:
        """按草稿 ID 获取或创建短期会话记忆。"""

        user = self._current_user()
        preview = self.db.scalars(
            select(DraftPreview).where(DraftPreview.id == draft_preview_id, DraftPreview.user_id == user.id)
        ).first()
        if preview is None:
            raise ValueError("草稿不存在。")

        session = self.db.scalars(
            select(ComposeSession)
            .options(joinedload(ComposeSession.messages))
            .where(ComposeSession.user_id == user.id, ComposeSession.draft_preview_id == draft_preview_id)
        ).unique().first()
        if session is not None:
            if editor_snapshot is not None:
                session.editor_snapshot = self._dump(editor_snapshot)
            if title and not session.title:
                session.title = title
            self.db.flush()
            return session

        return self.create_session(
            session_type=session_type,
            title=title or preview.subject,
            editor_snapshot=editor_snapshot or self.editor_snapshot_from_preview(preview),
            draft_preview_id=draft_preview_id,
        )

    def update_session(self, session_id: str, *, title: str | None = None, editor_snapshot: dict | None = None) -> ComposeSession:
        session = self._get_session(session_id)
        if title is not None:
            session.title = title
        if editor_snapshot is not None:
            session.editor_snapshot = self._dump(editor_snapshot)
        self.db.flush()
        return session

    def list_sessions(self, *, limit: int = 20, offset: int = 0) -> tuple[list[ComposeSession], int]:
        user = self._current_user()
        query = select(ComposeSession).where(ComposeSession.user_id == user.id).order_by(ComposeSession.updated_at.desc())
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.offset(offset).limit(limit)).all()
        return list(items), total

    def get_session(self, session_id: str) -> ComposeSession | None:
        user = self._current_user()
        return self.db.scalars(
            select(ComposeSession)
            .options(joinedload(ComposeSession.messages))
            .where(ComposeSession.id == session_id, ComposeSession.user_id == user.id)
        ).unique().first()

    def add_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        message_type: str = "normal",
        editor_snapshot: dict | None = None,
    ) -> ComposeMessage:
        session = self._get_session(session_id)
        snapshot = editor_snapshot or {}
        message = ComposeMessage(
            session_id=session.id,
            role=role,
            message_type=message_type,
            content=content,
            editor_snapshot=self._dump(snapshot),
            token_estimate=self.estimate_tokens(content),
        )
        self.db.add(message)
        if snapshot:
            session.editor_snapshot = self._dump(snapshot)
        self.db.flush()
        self.maybe_summarize(session)
        return message

    def add_message_for_draft(
        self,
        *,
        draft_preview_id: str,
        session_type: str,
        role: str,
        content: str,
        editor_snapshot: dict | None = None,
    ) -> tuple[ComposeSession, ComposeMessage]:
        """按草稿保存一条右侧 AI 对话消息。"""

        session = self.get_or_create_session_for_draft(
            draft_preview_id=draft_preview_id,
            session_type=session_type,
            editor_snapshot=editor_snapshot,
        )
        message = self.add_message(
            session.id,
            role=role,
            content=content,
            editor_snapshot=editor_snapshot,
        )
        return session, message

    def context_for_draft(self, *, draft_preview_id: str, recent_limit: int = 10) -> str:
        """为写作 Agent 组装短期记忆上下文。

        第十三阶段要求 AI Reply Workspace 与 Compose Mail 具备“连续会话感”。
        因此这里不能只把当前 editor_snapshot 发给模型，而要把：
        1. 会话摘要；
        2. 最近几轮未归档的用户/AI 消息；
        一起拼成一个紧凑上下文。这样模型在下一轮修改时，才能理解“之前为什么
        这样改、当前正文处于什么状态、用户又提出了什么新要求”。
        """

        user = self._current_user()
        session = self.db.scalars(
            select(ComposeSession).where(
                ComposeSession.user_id == user.id,
                ComposeSession.draft_preview_id == draft_preview_id,
            )
        ).first()
        if session is None:
            return ""

        recent_messages = list(
            self.db.scalars(
                select(ComposeMessage)
                .where(
                    ComposeMessage.session_id == session.id,
                    ComposeMessage.archived.is_(False),
                    ComposeMessage.message_type == "normal",
                )
                .order_by(ComposeMessage.created_at.desc())
                .limit(recent_limit)
            ).all()
        )
        recent_messages.reverse()
        lines: list[str] = []
        if session.summary:
            lines.append(f"此前对话摘要：{session.summary}")
        if recent_messages:
            lines.append("最近对话：")
            lines.extend(f"{msg.role}: {msg.content}" for msg in recent_messages)
        return "\n".join(lines)

    def maybe_summarize(self, session: ComposeSession) -> None:
        """当未归档对话过长时，压缩较早消息为会话摘要。"""

        visible_messages = list(
            self.db.scalars(
                select(ComposeMessage)
                .where(
                    ComposeMessage.session_id == session.id,
                    ComposeMessage.archived.is_(False),
                    ComposeMessage.message_type == "normal",
                )
                .order_by(ComposeMessage.created_at.asc())
            ).all()
        )
        total_chars = sum(len(msg.content or "") for msg in visible_messages)
        if len(visible_messages) <= self.max_visible_messages and total_chars <= self.max_visible_chars:
            return

        old_messages = visible_messages[:-self.keep_recent_messages]
        if not old_messages:
            return

        summary_input = [
            {"role": msg.role, "content": msg.content}
            for msg in old_messages
        ]
        result = self.memory_agent.summarize(
            existing_summary=session.summary or "",
            messages=summary_input,
            editor_snapshot=self._loads(session.editor_snapshot),
        )
        constraints = "\n".join(f"- {item}" for item in result.key_constraints)
        session.summary = result.summary if not constraints else f"{result.summary}\n关键约束：\n{constraints}"
        for msg in old_messages:
            msg.archived = True
        self.db.flush()

    def _get_session(self, session_id: str) -> ComposeSession:
        user = self._current_user()
        session = self.db.scalars(
            select(ComposeSession)
            .options(joinedload(ComposeSession.messages))
            .where(ComposeSession.id == session_id, ComposeSession.user_id == user.id)
        ).unique().first()
        if session is None:
            raise ValueError("写作会话不存在。")
        return session

    def _current_user(self) -> User:
        user = self.auth_service.get_current_user()
        if user is None:
            raise PermissionError("尚未连接 Google 账号。")
        return user

    @staticmethod
    def _dump(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _loads(value: str | dict | None) -> dict:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def estimate_tokens(value: str) -> int:
        """粗略估算 token 数，足够用于摘要触发阈值。"""

        return max(1, len(value or "") // 4)

    @staticmethod
    def editor_snapshot_from_preview(preview: DraftPreview) -> dict:
        return {
            "to": preview.to,
            "subject": preview.subject,
            "body": preview.body,
            "tone": preview.tone,
            "language": preview.language,
        }
