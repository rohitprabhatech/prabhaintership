import secrets
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from typing import Any
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.config import get_settings


password_hash = PasswordHash.recommended()
_dummy_password_hash: str | None = None


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hash.verify(password, encoded_hash)
    except Exception:
        return False


def verify_unknown_user_password(password: str) -> None:
    global _dummy_password_hash
    if _dummy_password_hash is None:
        _dummy_password_hash = password_hash.hash(secrets.token_urlsafe(32))
    password_hash.verify(password, _dummy_password_hash)


def create_access_token(admin_id: int, auth_version: int) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    claims: dict[str, Any] = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid4()),
        "ver": auth_version,
    }
    token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> tuple[int, int]:
    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "iat", "exp", "iss", "aud", "jti", "ver"]},
    )
    subject = claims.get("sub")
    auth_version = claims.get("ver")
    if (
        not isinstance(subject, str)
        or not subject.isdecimal()
        or not isinstance(auth_version, int)
        or isinstance(auth_version, bool)
        or auth_version < 0
    ):
        raise jwt.InvalidTokenError("Invalid subject")
    return int(subject), auth_version


def client_rate_limit_key(client_address: str) -> str:
    secret = get_settings().jwt_secret_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, client_address.encode("utf-8"), hashlib.sha256).hexdigest()