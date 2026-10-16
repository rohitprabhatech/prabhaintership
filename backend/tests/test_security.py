from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.security import decode_access_token, hash_password, verify_password


def test_password_hash_verifies_only_matching_password() -> None:
    encoded = hash_password("A-long-test-only-password-123!")

    assert encoded != "A-long-test-only-password-123!"
    assert verify_password("A-long-test-only-password-123!", encoded)
    assert not verify_password("incorrect-password", encoded)


def test_expired_access_token_is_rejected() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    expired_token = jwt.encode(
        {
            "sub": "1",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "jti": "expired-test-token",
            "ver": 0,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)