import re
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.admin import Admin
from app.security import hash_password


_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def _validated_username(username: str) -> str:
    normalized = username.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise APIError(
            400,
            "invalid_admin_username",
            "Admin username must be 3-64 lowercase letters, digits, dots, underscores, or hyphens",
        )
    return normalized


def validate_new_password(password: str, confirmation: str) -> None:
    if password != confirmation:
        raise APIError(400, "password_mismatch", "Passwords do not match")
    if len(password) < 12 or len(password) > 1024:
        raise APIError(400, "invalid_password_length", "Password must contain 12-1024 characters")


def bootstrap_admin(
    session: Session,
    username: str,
    email: str | None,
    password: str,
    confirmation: str,
) -> Admin:
    normalized_username = _validated_username(username)
    validate_new_password(password, confirmation)
    session.execute(text("LOCK TABLE internship_management.admins IN EXCLUSIVE MODE"))
    existing_admin_id = session.scalar(select(Admin.admin_id).limit(1))
    if existing_admin_id is not None:
        raise APIError(409, "admin_already_bootstrapped", "An Admin account is already provisioned")

    admin = Admin(
        username=normalized_username,
        email=email.strip().lower() if email else None,
        password_hash=hash_password(password),
        is_active=True,
        auth_version=0,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def reset_admin_password(
    session: Session,
    username: str,
    password: str,
    confirmation: str,
) -> Admin:
    normalized_username = _validated_username(username)
    validate_new_password(password, confirmation)
    admin = session.scalar(
        select(Admin).where(Admin.username == normalized_username).with_for_update()
    )
    if admin is None:
        raise APIError(404, "admin_not_found", "Admin account was not found")

    admin.password_hash = hash_password(password)
    admin.auth_version += 1
    admin.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(admin)
    return admin