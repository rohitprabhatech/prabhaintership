from uuid import UUID, uuid4

import pytest

from app.config import get_settings
from app.errors import APIError
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.security import client_rate_limit_key, hash_password, verify_password
from app.services.admin_provisioning import (
    bootstrap_admin,
    replace_admin_accounts,
    reset_admin_password,
)
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
    request_id = uuid4()
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "no-such-admin", "password": "invalid-password"},
        headers={"X-Request-ID": str(request_id)},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
    assert "no-such-admin" not in response.text
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            action="admin_login",
            outcome="failure",
            request_id=UUID(response.headers["X-Request-ID"]),
        )
        .one()
    )
    assert audit.actor_admin_id is None
    assert audit.metadata_ == {"reason": "invalid_credentials"}


@pytest.mark.integration
def test_successful_admin_login_is_audited_without_username(api_client, db_session) -> None:
    username = f"audit-{uuid4().hex}"
    admin = Admin(
        username=username,
        password_hash=hash_password("Audit-test-password-123!"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Audit-test-password-123!"},
    )

    assert response.status_code == 200
    audit = (
        db_session.query(AuditLog)
        .filter_by(
            actor_admin_id=admin.admin_id,
            action="admin_login",
            outcome="success",
        )
        .one()
    )
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
def test_authenticated_admin_can_change_password_and_must_sign_in_again(
    api_client, db_session
) -> None:
    old_password = "Current-test-password-123!"
    new_password = "Changed-test-password-456!"
    admin = Admin(
        username=f"change-password-{uuid4().hex}",
        password_hash=hash_password(old_password),
        is_active=True,
        auth_version=0,
    )
    other_admin = Admin(
        username=f"other-password-{uuid4().hex}",
        password_hash=hash_password("Other-test-password-789!"),
        is_active=True,
        auth_version=0,
    )
    db_session.add_all([admin, other_admin])
    db_session.commit()
    other_hash = other_admin.password_hash

    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": old_password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = api_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "admin_id": other_admin.admin_id,
            "current_password": old_password,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password changed. Sign in again with your new password.",
        "reauthenticate": True,
    }
    assert old_password not in response.text
    assert new_password not in response.text
    assert "password_hash" not in response.text

    db_session.expire_all()
    db_session.refresh(admin)
    db_session.refresh(other_admin)
    assert admin.auth_version == 1
    assert admin.password_hash != old_password
    assert verify_password(new_password, admin.password_hash)
    assert not verify_password(old_password, admin.password_hash)
    assert other_admin.password_hash == other_hash

    revoked = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked.status_code == 401

    old_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": old_password},
    )
    new_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": new_password},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


@pytest.mark.integration
def test_change_password_rejects_wrong_current_password(api_client, db_session) -> None:
    password = "Current-test-password-123!"
    admin = Admin(
        username=f"wrong-current-{uuid4().hex}",
        password_hash=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": password},
    )

    response = api_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={
            "current_password": "Incorrect-current-password!",
            "new_password": "Changed-test-password-456!",
            "confirm_password": "Changed-test-password-456!",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "current_password_incorrect"
    assert "Incorrect-current-password!" not in response.text
    db_session.expire(admin)
    assert verify_password(password, admin.password_hash)


@pytest.mark.integration
def test_change_password_rejects_mismatch_weak_and_reused_passwords(
    api_client, db_session
) -> None:
    password = "Current-test-password-123!"
    admin = Admin(
        username=f"password-validation-{uuid4().hex}",
        password_hash=hash_password(password),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": password},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    base_payload = {
        "current_password": password,
        "new_password": "Changed-test-password-456!",
        "confirm_password": "Changed-test-password-456!",
    }

    mismatch = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={**base_payload, "confirm_password": "Different-confirmation-789!"},
    )
    weak = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={**base_payload, "new_password": "short", "confirm_password": "short"},
    )
    reused = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": password,
            "new_password": password,
            "confirm_password": password,
        },
    )
    missing = api_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": password,
            "new_password": "",
            "confirm_password": "",
        },
    )

    assert mismatch.status_code == 400
    assert mismatch.json()["code"] == "password_mismatch"
    assert weak.status_code == 400
    assert weak.json()["code"] == "invalid_password_length"
    assert reused.status_code == 400
    assert reused.json()["code"] == "password_unchanged"
    assert missing.status_code == 422
    assert password not in missing.text
    assert "short" not in weak.text


@pytest.mark.integration
def test_change_password_requires_authentication(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Current-test-password-123!",
            "new_password": "Changed-test-password-456!",
            "confirm_password": "Changed-test-password-456!",
        },
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_change_password_database_failure_does_not_persist(
    api_client, db_session, monkeypatch
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    import app.api.routes.auth as auth_route

    password = "Current-test-password-123!"
    admin = Admin(
        username=f"password-db-failure-{uuid4().hex}",
        password_hash=hash_password(password),
        is_active=True,
        auth_version=0,
    )
    db_session.add(admin)
    db_session.commit()
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": password},
    )

    def fail_rate_limit_reset(_session, _key_hash):
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(auth_route, "reset_login_rate_limit", fail_rate_limit_reset)
    with pytest.raises(SQLAlchemyError):
        api_client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            json={
                "current_password": password,
                "new_password": "Changed-test-password-456!",
                "confirm_password": "Changed-test-password-456!",
            },
        )

    db_session.expire(admin)
    assert admin.auth_version == 0
    assert verify_password(password, admin.password_hash)


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
def test_admin_replacement_preserves_history_and_authenticates_new_account(
    api_client, db_session
) -> None:
    username_suffix = uuid4().hex
    old_password = "Existing-admin-password-123!"
    old_admins = [
        Admin(
            username=f"replacement-{username_suffix}-{index}",
            email=f"replacement-{username_suffix}-{index}@example.com",
            password_hash=hash_password(old_password),
            is_active=True,
            auth_version=0,
        )
        for index in (1, 2)
    ]
    db_session.add_all(old_admins)
    db_session.commit()
    active_admin_count = db_session.query(Admin).filter_by(is_active=True).count()

    db_session.add(
        AuditLog(
            actor_admin_id=old_admins[0].admin_id,
            action="replacement_history_test",
            target_type="admin",
            target_id=old_admins[0].admin_id,
            outcome="success",
            metadata_={},
        )
    )
    db_session.commit()

    old_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": old_admins[0].username, "password": old_password},
    )
    assert old_login.status_code == 200
    old_token = old_login.json()["access_token"]

    password = "New-replacement-password-456!"
    replacement_username = f"prabhatech-{username_suffix[:8]}"
    replacement_email = f"{replacement_username}@gmail.com"
    confirmation_phrase = (
        f"DEACTIVATE ALL {active_admin_count} ACTIVE ADMINS AND CREATE "
        f"{replacement_username.upper()}"
    )
    replacement, deactivated_count = replace_admin_accounts(
        db_session,
        replacement_username,
        replacement_email,
        password,
        password,
        active_admin_count,
        confirmation_phrase,
    )

    assert deactivated_count == active_admin_count
    assert replacement.username == replacement_username
    assert replacement.email == replacement_email
    assert replacement.is_active is True
    db_session.expire_all()
    for old_admin in old_admins:
        db_session.refresh(old_admin)
        assert old_admin.is_active is False
        assert old_admin.auth_version == 1

    retained_history = (
        db_session.query(AuditLog)
        .filter_by(action="replacement_history_test", actor_admin_id=old_admins[0].admin_id)
        .one()
    )
    assert retained_history.actor_admin_id == old_admins[0].admin_id

    revoked = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert revoked.status_code == 401

    new_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": replacement_username, "password": password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["admin"]["username"] == replacement_username
    assert new_login.json()["admin"]["email"] == replacement_email

    new_identity = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_login.json()['access_token']}"},
    )
    assert new_identity.status_code == 200
    assert new_identity.json()["username"] == replacement_username


@pytest.mark.integration
def test_admin_replacement_rolls_back_when_admin_set_changed(db_session) -> None:
    existing = Admin(
        username=f"replacement-guard-{uuid4().hex}",
        password_hash=hash_password("Existing-admin-password-123!"),
        is_active=True,
        auth_version=0,
    )
    db_session.add(existing)
    db_session.commit()
    expected_active_count = db_session.query(Admin).filter_by(is_active=True).count() + 1
    target_username = f"replacement-target-{uuid4().hex[:8]}"
    target_email = f"{target_username}@example.com"
    confirmation_phrase = (
        f"DEACTIVATE ALL {expected_active_count} ACTIVE ADMINS AND CREATE "
        f"{target_username.upper()}"
    )
    db_session.rollback()

    with pytest.raises(APIError) as error:
        replace_admin_accounts(
            db_session,
            target_username,
            target_email,
            "New-replacement-password-456!",
            "New-replacement-password-456!",
            expected_active_count,
            confirmation_phrase,
        )

    assert error.value.code == "admin_set_changed"
    db_session.refresh(existing)
    assert existing.is_active is True
    assert (
        db_session.query(Admin)
        .filter_by(username=target_username)
        .count()
        == 0
    )


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
