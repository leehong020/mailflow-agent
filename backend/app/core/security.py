"""安全工具模块。

当前阶段只做 OAuth token 的加密与解密。
数据库中不会明文保存 access_token / refresh_token。
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet_key() -> bytes:
    """生成 token 加密密钥。

    生产环境建议显式配置 FERNET_KEY；开发环境如果未配置，则从 APP_SECRET_KEY
    派生稳定密钥，避免重启后无法解密本地 token。
    """

    settings = get_settings()
    if settings.fernet_key:
        return settings.fernet_key.encode("utf-8")

    digest = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_text(value: str) -> str:
    """加密字符串，返回可存入数据库的文本。"""

    return Fernet(_fernet_key()).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    """解密数据库中的密文 token。"""

    return Fernet(_fernet_key()).decrypt(value.encode("utf-8")).decode("utf-8")
