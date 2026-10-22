import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import or_, select, text, update
from sqlalchemy.orm import Session

from app.config import get_admin_provisioning_settings
from app.errors import APIError
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.security import hash_password, verify_password

_USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def normalize_admin_username(username: str) -> str:
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


def normalize_admin_email(email: str) -> str:
    try:
        return str(TypeAdapter(EmailStr).validate_python(email.strip())).lower()
    except ValidationError:
        raise APIError(400, "invalid_admin_email", "Admin email address is invalid") from None


@contextmanager
def _admin_provisioning_lock(session: Session) -> Iterator[None]:
    settings = get_admin_provisioning_settings()
    database_url = settings.database_url
    lock_scope = f"{database_url.host}:{database_url.port}/{database_url.database}"
    lock_name = "prabhatech-admin-provisioning-" + sha256(
        lock_scope.encode("utf-8")
    ).hexdigest()[:24]
    bind = session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    with engine.connect() as lock_connection:
        acquired = lock_connection.scalar(
            text("SELECT GET_LOCK(:lock_name, 10)"), {"lock_name": lock_name}
        )
        if acquired != 1:
            raise APIError(503, "admin_provisioning_lock_unavailable", "Admin provisioning is busy")
        try:
            yield
        finally:
            lock_connection.scalar(
                text("SELECT RELEASE_LOCK(:lock_name)"), {"lock_name": lock_name}
            )


def bootstrap_admin(
    session: Session,
    username: str,
    email: str | None,
    password: str,
    confirmation: str,
) -> Admin:
    normalized_username = normalize_admin_username(username)
    validate_new_password(password, confirmation)
    normalized_email = normalize_admin_email(email) if email else None
    with _admin_provisioning_lock(session):
        existing_admin_id = session.scalar(select(Admin.admin_id).limit(1))
        if existing_admin_id is not None:
            raise APIError(
                409, "admin_already_bootstrapped", "An Admin account is already provisioned"
            )

        admin = Admin(
            username=normalized_username,
            email=normalized_email,
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
    normalized_username = normalize_admin_username(username)
    validate_new_password(password, confirmation)
    with _admin_provisioning_lock(session):
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


def replace_admin_accounts(
    session: Session,
    username: str,
    email: str,
    password: str,
    password_confirmation: str,
    expected_active_admin_count: int,
    confirmation_phrase: str,
) -> tuple[Admin, int]:
    normalized_username = normalize_admin_username(username)
    normalized_email = normalize_admin_email(email)
    validate_new_password(password, password_confirmation)
    if expected_active_admin_count < 1:
        raise APIError(400, "no_admins_to_replace", "No existing Admin accounts were found")

    expected_confirmation = (
        f"DEACTIVATE ALL {expected_active_admin_count} ACTIVE ADMINS AND CREATE "
        f"{normalized_username.upper()}"
    )
    if confirmation_phrase != expected_confirmation:
        raise APIError(
            400,
            "admin_replacement_not_confirmed",
            "Admin replacement was not confirmed",
        )
    if session.in_transaction():
        raise APIError(
            409,
            "admin_replacement_requires_clean_session",
            "Admin replacement requires a session with no active transaction",
        )

    with _admin_provisioning_lock(session):
        try:
            with session.begin():
                existing_admins = list(
                    session.scalars(select(Admin).order_by(Admin.admin_id).with_for_update())
                )
                active_admins = [admin for admin in existing_admins if admin.is_active]
                if len(active_admins) != expected_active_admin_count:
                    raise APIError(
                        409,
                        "admin_set_changed",
                        "The Admin account set changed; inspect it again before retrying",
                    )

                duplicate = session.scalar(
                    select(Admin.admin_id).where(
                        or_(
                            Admin.username == normalized_username,
                            Admin.email_normalized == normalized_email,
                        )
                    )
                )
                if duplicate is not None:
                    raise APIError(
                        409,
                        "admin_identity_exists",
                        "The requested Admin username or email already exists",
                    )

                new_password_hash = hash_password(password)
                replacement = Admin(
                    username=normalized_username,
                    email=normalized_email,
                    password_hash=new_password_hash,
                    is_active=True,
                    auth_version=0,
                )
                session.add(replacement)
                session.flush()
                if not verify_password(password, replacement.password_hash):
                    raise APIError(
                        500,
                        "admin_password_hash_verification_failed",
                        "New Admin password verification failed",
                    )

                active_ids = [admin.admin_id for admin in active_admins]
                result = session.execute(
                    update(Admin)
                    .where(Admin.admin_id.in_(active_ids), Admin.is_active.is_(True))
                    .values(
                        is_active=False,
                        auth_version=Admin.auth_version + 1,
                        updated_at=datetime.now(UTC),
                    )
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != expected_active_admin_count:
                    raise APIError(
                        409,
                        "admin_set_changed",
                        "The Admin account set changed; replacement was rolled back",
                    )

                session.add(
                    AuditLog(
                        actor_admin_id=None,
                        action="admin_accounts_replaced",
                        target_type="admin",
                        target_id=replacement.admin_id,
                        outcome="success",
                        metadata_={
                            "deactivated_admin_count": expected_active_admin_count
                        },
                    )
                )
            session.expire_all()
            return replacement, expected_active_admin_count
        except Exception:
            session.rollback()
            raise