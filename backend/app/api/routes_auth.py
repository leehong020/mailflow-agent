"""Google OAuth 相关 HTTP 接口。

第二阶段的完整授权链路：
前端 Settings 点击连接 Google
    -> GET /api/v1/auth/google/login
    -> 后端生成 state 并跳转 Google 授权页
    -> Google 回调 /api/v1/auth/google/callback
    -> 后端校验 state、换取 token、读取用户资料、加密保存 token
    -> 跳回前端 Settings 页面
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.google_provider import GoogleOAuthProvider
from app.schemas.auth import GoogleConnectionStatus
from app.services.auth_service import AuthService
from app.services.google_service import GoogleService

router = APIRouter(prefix="/auth", tags=["auth"])
REQUIRED_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _scope_set(value: str | list[str] | tuple[str, ...] | None) -> set[str]:
    """把 Google 返回的 scope 转成集合，便于判断是否授权 Gmail 权限。"""

    if value is None:
        return set()
    if isinstance(value, str):
        # Google 回调 URL 中的 scope 使用空格分隔；项目 .env 中使用逗号分隔。
        normalized = value.replace(",", " ")
        return {item.strip() for item in normalized.split(" ") if item.strip()}
    return {item.strip() for item in value if item.strip()}


def _state_serializer() -> URLSafeTimedSerializer:
    """创建 OAuth state 签名器。

    state 用来防止 CSRF。我们用 APP_SECRET_KEY 对 state 做签名，
    回调时必须能验签成功，才会继续换取 Google token。
    """

    return URLSafeTimedSerializer(get_settings().app_secret_key, salt="google-oauth-state")


@router.get("/google/login")
def google_login() -> RedirectResponse:
    """跳转到 Google OAuth 授权页。"""

    provider = GoogleOAuthProvider()

    # PKCE 的 code_verifier 必须从登录请求保存到回调请求。
    # 这里把它放进已签名的 state，避免服务端额外引入 session 存储。
    code_verifier = provider.generate_code_verifier()

    # 这里的 source 只是保留字段，后续如果有多个入口可以区分来源页面。
    state = _state_serializer().dumps({"source": "settings", "code_verifier": code_verifier})
    try:
        authorization = provider.build_authorization_url(state=state, code_verifier=code_verifier)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return RedirectResponse(authorization.url)


@router.get("/google/callback")
def google_callback(request: Request, state: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """处理 Google OAuth 回调，校验 state 后保存加密 token。"""

    return complete_google_callback(request=request, state=state, db=db)


def complete_google_callback(request: Request, state: str, db: Session) -> RedirectResponse:
    """完成 Google OAuth 回调的公共逻辑。

    项目实际对外回调地址使用 /gmail/auth/callback；
    /api/v1/auth/google/callback 作为兼容地址保留，便于调试和旧配置迁移。
    """

    settings = get_settings()

    # 先校验 state，失败说明请求不是从本系统发起，直接拒绝。
    try:
        state_payload = _state_serializer().loads(state, max_age=600)
    except BadSignature as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state 校验失败。") from exc

    code_verifier = state_payload.get("code_verifier")
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state 中缺少 PKCE code_verifier，请从 Settings 页面重新发起登录。",
        )

    # Google 回调会带上本次用户实际授予的 scope。
    # 如果这里没有 gmail.readonly，就算后续换 token 成功，也无法读取 Gmail。
    callback_scopes = _scope_set(request.query_params.get("scope"))
    if callback_scopes and REQUIRED_GMAIL_SCOPE not in callback_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Google 未授予 Gmail 读取权限。请在 Google Cloud Console 的 "
                "OAuth consent screen / Data Access 中添加 Gmail API 的 "
                "https://www.googleapis.com/auth/gmail.readonly scope，并确认已启用 Gmail API，"
                "然后从 Settings 页面重新连接 Google。"
            ),
        )

    provider = GoogleOAuthProvider()

    # 用 Google 回调 URL 中的 code 换取 access_token / refresh_token。
    credentials = provider.fetch_token(str(request.url), code_verifier=code_verifier)

    granted_scopes = _scope_set(getattr(credentials, "granted_scopes", None))
    if granted_scopes and REQUIRED_GMAIL_SCOPE not in granted_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token 中缺少 Gmail 读取权限，请检查 OAuth consent screen 的 scope 配置。",
        )

    # 读取 Google 用户基本信息，用 email 作为当前阶段的账号标识。
    profile = GoogleService(db).get_user_profile(credentials)

    # token 会在 AuthService 内部加密后写入数据库。
    AuthService(db).save_google_user(profile=profile, credentials=credentials)
    return RedirectResponse(f"{settings.frontend_base_url.rstrip('/')}/settings?google=connected")


@router.get("/google/status", response_model=GoogleConnectionStatus)
def google_status(db: Session = Depends(get_db)) -> GoogleConnectionStatus:
    """Settings 页面使用的 Google 连接状态。"""

    user = AuthService(db).get_current_user()
    if user is None:
        return GoogleConnectionStatus(connected=False)

    return GoogleConnectionStatus(
        connected=True,
        email=user.email,
        name=user.name,
        picture=user.picture,
        scopes=[scope for scope in user.google_scopes.split(",") if scope],
    )


@router.post("/google/disconnect")
def google_disconnect(db: Session = Depends(get_db)) -> dict[str, str]:
    """断开本地 Google 连接；不会删除 Google 账号中的任何数据。"""

    # 当前操作只删除本地保存的用户与 token，不会调用 Gmail 删除任何邮件。
    AuthService(db).disconnect_google()
    return {"status": "disconnected"}
