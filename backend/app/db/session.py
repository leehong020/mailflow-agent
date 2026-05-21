"""数据库连接与 Session 管理。

路由函数通过 Depends(get_db) 获得数据库会话。
这样每个 HTTP 请求都有独立 Session，请求结束后自动关闭。
"""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

# SessionLocal 是数据库会话工厂，不是具体连接。
# FastAPI 每个请求进来时，由 get_db 创建一个 Session。
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """阶段一先自动建表；后续进入生产形态时再接入 Alembic 迁移。"""

    from app.models.calendar import CalendarSuggestion  # noqa: F401
    from app.models.compose import ComposeMessage, ComposeSession  # noqa: F401
    from app.models.draft import DraftPreview, PendingAction  # noqa: F401
    from app.models.email import EmailAnalysis, EmailRecord, TaskItem  # noqa: F401
    from app.models.trace import AgentTrace, AgentTraceEvent  # noqa: F401
    from app.models.user import User  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_lightweight_migrations()


def _ensure_sqlite_lightweight_migrations() -> None:
    """为本地 SQLite 演示库补齐新增列。

    课程项目当前暂不引入 Alembic。`create_all` 只能创建新表，不能修改已存在
    的表；因此第九阶段给 email_records 新增 Gmail 操作状态字段时，需要在
    SQLite 下做一次轻量 ALTER TABLE。PostgreSQL 后续接入 Alembic 时可移除。
    """

    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        if inspector.has_table("compose_sessions"):
            existing_session_columns = {column["name"] for column in inspector.get_columns("compose_sessions")}
            session_migrations = {
                "draft_preview_id": "ALTER TABLE compose_sessions ADD COLUMN draft_preview_id VARCHAR(36) DEFAULT ''",
                "summary": "ALTER TABLE compose_sessions ADD COLUMN summary TEXT DEFAULT ''",
            }
            for column_name, ddl in session_migrations.items():
                if column_name not in existing_session_columns:
                    connection.execute(text(ddl))

        if inspector.has_table("compose_messages"):
            existing_message_columns = {column["name"] for column in inspector.get_columns("compose_messages")}
            message_migrations = {
                "message_type": "ALTER TABLE compose_messages ADD COLUMN message_type VARCHAR(24) DEFAULT 'normal'",
                "editor_snapshot": "ALTER TABLE compose_messages ADD COLUMN editor_snapshot TEXT DEFAULT '{}'",
                "token_estimate": "ALTER TABLE compose_messages ADD COLUMN token_estimate INTEGER DEFAULT 0",
                "archived": "ALTER TABLE compose_messages ADD COLUMN archived BOOLEAN DEFAULT 0",
            }
            for column_name, ddl in message_migrations.items():
                if column_name not in existing_message_columns:
                    connection.execute(text(ddl))

        existing_email_columns = {column["name"] for column in inspector.get_columns("email_records")}
        email_migrations = {
            "label_ids": "ALTER TABLE email_records ADD COLUMN label_ids JSON DEFAULT '[]'",
            "is_read": "ALTER TABLE email_records ADD COLUMN is_read BOOLEAN DEFAULT 1",
            "is_starred": "ALTER TABLE email_records ADD COLUMN is_starred BOOLEAN DEFAULT 0",
            "mailbox_status": "ALTER TABLE email_records ADD COLUMN mailbox_status VARCHAR(32) DEFAULT 'inbox'",
        }
        for column_name, ddl in email_migrations.items():
            if column_name not in existing_email_columns:
                connection.execute(text(ddl))


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖项：创建并在请求结束后关闭数据库 Session。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
