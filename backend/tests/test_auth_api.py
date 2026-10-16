from uuid import uuid4

import pytest

from app.config import get_settings
from app.errors import APIError
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.security import client_rate_limit_key, hash_password
from app.services.admin_provisioning import bootstrap_admin, reset_admin_password
from app.services.login_rate_limiter import (
    check_login_rate_limit,
    record_login_failure,
    reset_login_rate_limit,
)


@pytest.mark.integration
def test_admin_login_and_protected_identity(api_client, db_session) -> None:
    username = f"test-{uuid4().hex}"
    admin = Admin(
        username=username,
        password_hash=hash_password("Test-only-long-password-123!"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Test-only-long-password-123!"},
    )

    assert login.status_code == 200
    token = login.json()["access_token"]
    identity = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert identity.status_code == 200
    assert identity.json()["username"] == username

    denied = api_client.get("/api/v1/auth/me")
    assert denied.status_code == 401


@pytest.mark.integration
def test_invalid_admin_credentials_are_generic_and_audited(api_client, db_session) -> None:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "no-such-admin", "password": "invalid-password"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert "no-such-admin" not in response.text
    audit = db_session.query(AuditLog).filter_by(action="admin_login", outcome="failure").one()
    assert audit.actor_admin_id is None
    assert audit.metadata_ == {"reason": "invalid_credentials"}


@pytest.mark.integration
def test_successful_admin_login_is_audited_without_username(api_client, db_session) -> None:
    username = f"audit-{uuid4().hex}"
    db_session.add(
        Admin(
            username=username,
            password_hash=hash_password("Audit-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()

    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Audit-test-password-123!"},
    )

    assert response.status_code == 200
    audit = db_session.query(AuditLog).filter_by(action="admin_login", outcome="success").one()
    assert audit.target_type == "admin"
    assert username not in str(audit.metadata_)


@pytest.mark.integration
def test_password_reset_revokes_existing_access_tokens(api_client, db_session) -> None:
    username = f"reset-{uuid4().hex}"
    db_session.add(
        Admin(
            username=username,
            password_hash=hash_password("Old-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()

    old_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Old-test-password-123!"},
    )
    old_token = old_login.json()["access_token"]

    reset_admin_password(
        db_session,
        username,
        "New-test-password-456!",
        "New-test-password-456!",
    )

    revoked = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert revoked.status_code == 401
    assert revoked.json()["code"] == "invalid_token"

    old_password = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Old-test-password-123!"},
    )
    new_password = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "New-test-password-456!"},
    )
    assert old_password.status_code == 401
    assert new_password.status_code == 200


@pytest.mark.integration
def test_bootstrap_rejects_second_admin(api_client, db_session) -> None:
    db_session.add(
        Admin(
            username=f"bootstrap-{uuid4().hex}",
            password_hash=hash_password("Existing-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()

    with pytest.raises(APIError) as error:
        bootstrap_admin(
            db_session,
            "second-admin",
            None,
            "Another-test-password-456!",
            "Another-test-password-456!",
        )

    assert error.value.code == "admin_already_bootstrapped"


@pytest.mark.integration
def test_login_rate_limiter_blocks_after_configured_failures(db_session) -> None:
    key = client_rate_limit_key(f"rate-test-{uuid4().hex}")
    for _ in range(get_settings().auth_rate_limit_attempts):
        assert check_login_rate_limit(db_session, key).allowed
        record_login_failure(db_session, key)

    decision = check_login_rate_limit(db_session, key)
    reset_login_rate_limit(db_session, key)

    assert decision.allowed is False
    assert decision.retry_after > 0


@pytest.mark.integration
def test_login_endpoint_returns_429_after_failures(api_client, db_session, monkeypatch) -> None:
    key = client_rate_limit_key("testclient")
    reset_login_rate_limit(db_session, key)
    monkeypatch.setattr(get_settings(), "auth_rate_limit_attempts", 1)

    first = api_client.post(
        "/api/v1/auth/login",
        json={"username": "missing-admin", "password": "invalid-password"},
    )
    second = api_client.post(
        "/api/v1/auth/login",
        json={"username": "missing-admin", "password": "invalid-password"},
    )
    reset_login_rate_limit(db_session, key)

    assert first.status_code == 401
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0
