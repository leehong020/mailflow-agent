"""应用配置模块。

所有可变配置都从 .env 或环境变量读取，例如：
- 后端 / 前端地址；
- 数据库连接；
- Google OAuth JSON 文件路径；
- Google API scope；
- token 加密密钥。

把配置集中在这里，可以避免业务代码到处读取 os.environ。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """统一管理应用配置，避免在业务代码中散落读取环境变量。"""

    # 应用名称会显示在 Swagger 文档标题中。
    app_name: str = "MailFlow Agent"

    # 用于 OAuth state 签名和开发环境 token 加密密钥派生。
    # 本地 .env 中必须换成自己的随机字符串。
    app_secret_key: str = Field(default="change-me-in-local-env")

    # Fernet 标准密钥；如果配置了它，会优先用于 token 加密。
    fernet_key: str | None = None

    # 前后端基础地址用于 CORS、OAuth 回调、前端跳转。
    backend_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"

    # 第一二阶段默认 SQLite，保证不启动 PostgreSQL 也能演示。
    database_url: str = "sqlite:///./mailflow_agent.db"
    redis_url: str = "redis://localhost:6379/0"

    # 大模型配置。DashScope 兼容 OpenAI Chat Completions 协议，
    # 因此这里使用 openai Python SDK 调用。
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str | None = None
    llm_model: str = "qwen-plus"
    llm_timeout_seconds: float = 30.0

    # Google OAuth Client JSON 的默认位置。
    # 从 backend 目录启动时，../secrets 会指向项目根目录的 secrets。
    google_oauth_client_file: str = "../secrets/google_oauth_client.json"
    google_redirect_uri_value: str | None = Field(default=None, validation_alias="GOOGLE_REDIRECT_URI")
    google_scopes: str = (
        "openid,"
        "https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/userinfo.profile,"
        "https://www.googleapis.com/auth/gmail.readonly,"
        "https://www.googleapis.com/auth/gmail.compose,"
        "https://www.googleapis.com/auth/gmail.send,"
        "https://www.googleapis.com/auth/gmail.modify,"
        "https://www.googleapis.com/auth/calendar.readonly,"
        "https://www.googleapis.com/auth/calendar.events"
    )
    allow_insecure_oauth_local: bool = True

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def google_scope_list(self) -> list[str]:
        """把逗号分隔的 scope 字符串转成 Google SDK 需要的列表。"""

        return [scope.strip() for scope in self.google_scopes.split(",") if scope.strip()]

    @property
    def resolved_google_redirect_uri(self) -> str:
        """Google Cloud Console 中必须配置的 OAuth 回调地址。"""

        if self.google_redirect_uri_value:
            return self.google_redirect_uri_value
        return f"{self.backend_base_url.rstrip('/')}/gmail/auth/callback"

    @property
    def google_oauth_client_path(self) -> Path:
        """支持相对 backend 目录或项目根目录配置 OAuth JSON 路径。"""

        raw_path = Path(self.google_oauth_client_file).expanduser()
        if raw_path.is_absolute():
            return raw_path

        backend_dir = Path(__file__).resolve().parents[2]
        project_root = backend_dir.parent
        candidates = [backend_dir / raw_path, project_root / raw_path]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return candidates[0].resolve()


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求都重新解析 .env。"""

    return Settings()
