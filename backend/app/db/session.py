"""数据库连接与 Session 管理。

路由函数通过 Depends(get_db) 获得数据库会话。
这样每个 HTTP 请求都有独立 Session，请求结束后自动关闭。
"""

from collections.abc import Generator

from sqlalchemy import create_engine
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
    from app.models.draft import DraftPreview, PendingAction  # noqa: F401
    from app.models.email import EmailAnalysis, EmailRecord, TaskItem  # noqa: F401
    from app.models.trace import AgentTrace, AgentTraceEvent  # noqa: F401
    from app.models.user import User  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖项：创建并在请求结束后关闭数据库 Session。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
