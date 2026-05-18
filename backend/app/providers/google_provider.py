"""Google OAuth Provider。

Provider 层负责直接接触第三方 SDK。
这样 FastAPI 路由不用关心 Google SDK 的创建细节，后续如果要支持其他邮箱服务，
可以新增 Provider，而不是改动已有路由结构。
"""

import os
import secrets
import string
from dataclasses import dataclass

from google_auth_oauthlib.flow import Flow

from app.core.config import get_settings


@dataclass(frozen=True)
class AuthorizationUrl:
    """Google 授权链接和 state 的简单封装。"""

    url: str
    state: str


class GoogleOAuthProvider:
    """Google OAuth SDK 封装，路由层不直接操作第三方 SDK。"""

    def __init__(self) -> None:
        self.settings = get_settings()

        # Google OAuth 默认要求 HTTPS。
        # 本地开发使用 http://localhost 时，需要开启 OAUTHLIB_INSECURE_TRANSPORT。
        if self.settings.allow_insecure_oauth_local:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

        # Google 可能只返回用户实际授予的 scope。
        # 我们会在业务层主动校验 Gmail scope 是否存在，因此这里让 oauthlib
        # 不要因为 scope 变化直接抛 Warning 导致用户看到 500。
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    @staticmethod
    def generate_code_verifier(length: int = 96) -> str:
        """生成 PKCE code_verifier。

        google-auth-oauthlib 会在授权 URL 中加入 code_challenge。
        Google 回调后换 token 时必须提交同一个 code_verifier，否则会报：
        invalid_grant: Missing code verifier。

        code_verifier 允许字符来自 RFC 7636：A-Z / a-z / 0-9 / -._~。
        """

        alphabet = string.ascii_letters + string.digits + "-._~"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _flow(self, code_verifier: str | None = None) -> Flow:
        """根据 OAuth JSON 创建 Google OAuth Flow。"""

        client_file = self.settings.google_oauth_client_path
        if not client_file.exists():
            raise FileNotFoundError(
                f"未找到 Google OAuth JSON 文件：{client_file}。请放到 secrets/google_oauth_client.json。"
            )
        return Flow.from_client_secrets_file(
            str(client_file),
            scopes=self.settings.google_scope_list,
            redirect_uri=self.settings.resolved_google_redirect_uri,
            code_verifier=code_verifier,
            autogenerate_code_verifier=code_verifier is None,
        )

    def build_authorization_url(self, state: str, code_verifier: str) -> AuthorizationUrl:
        """生成 Google 授权页面 URL。"""

        flow = self._flow(code_verifier=code_verifier)

        # access_type=offline 用于获取 refresh_token，方便 token 过期后自动刷新。
        # prompt=consent 在开发阶段能更稳定地拿到 refresh_token。
        url, generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return AuthorizationUrl(url=url, state=generated_state)

    def fetch_token(self, authorization_response: str, code_verifier: str):
        """使用 Google 回调 URL 中的 code 换取 token。"""

        flow = self._flow(code_verifier=code_verifier)
        flow.fetch_token(authorization_response=authorization_response)
        return flow.credentials
