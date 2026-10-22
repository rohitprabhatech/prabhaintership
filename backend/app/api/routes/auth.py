import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.errors import APIError
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.schemas.auth import (
    AdminPublic,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
)
from app.security import client_rate_limit_key, create_access_token, hash_password, verify_password
from app.services.auth_service import authenticate_admin
from app.services.login_rate_limiter import (
    check_login_rate_limit,
    record_login_failure,
    reset_login_rate_limit,
)

router = APIRouter()
logger = logging.getLogger("app.auth")


def _request_id(request: Request) -> UUID | None:
    try:
        return UUID(request.state.request_id)
    except (AttributeError, ValueError):
        return None


@router.post("/login", response_model=LoginResponse, summary="Authenticate an Admin")
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_db),
) -> LoginResponse:
    client_address = request.client.host if request.client else "unknown"
    rate_limit_key = client_rate_limit_key(client_address)
    decision = check_login_rate_limit(session, rate_limit_key)
    if not decision.allowed:
        logger.warning("Admin login rate limited", extra={"event": "admin_login_rate_limited"})
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(decision.retry_after)},
            content={
                "type": "about:blank",
                "title": "Too many requests",
                "status": 429,
                "code": "login_rate_limited",
                "request_id": getattr(request.state, "request_id", "-"),
            },
        )

    admin = authenticate_admin(session, payload.username, payload.password.get_secret_value())
    if admin is None:
        record_login_failure(session, rate_limit_key)
        session.add(
            AuditLog(
                actor_admin_id=None,
                action="admin_login",
                target_type="authentication",
                outcome="failure",
                request_id=_request_id(request),
                metadata_={"reason": "invalid_credentials"},
            )
        )
        session.commit()
        logger.warning("Admin login failed", extra={"event": "admin_login_failed"})
        raise APIError(401, "invalid_credentials", "Username or password is incorrect")

    reset_login_rate_limit(session, rate_limit_key)
    session.add(
        AuditLog(
            actor_admin_id=admin.admin_id,
            action="admin_login",
            target_type="admin",
            target_id=admin.admin_id,
            outcome="success",
            request_id=_request_id(request),
            metadata_={},
        )
    )
    session.commit()
    logger.info("Admin login succeeded", extra={"event": "admin_login_succeeded"})
    token, expires_in = create_access_token(admin.admin_id, admin.auth_version)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        admin=AdminPublic.model_validate(admin),
    )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change the authenticated Admin password",
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    session: Session = Depends(get_db),
) -> ChangePasswordResponse:
    client_address = request.client.host if request.client else "unknown"
    rate_limit_key = client_rate_limit_key(client_address)
    decision = check_login_rate_limit(session, rate_limit_key)
    if not decision.allowed:
        raise APIError(
            429,
            "login_rate_limited",
            "Too many password verification attempts. Try again later.",
        )

    current_password = payload.current_password.get_secret_value()
    new_password = payload.new_password.get_secret_value()
    confirmation = payload.confirm_password.get_secret_value()

    if not verify_password(current_password, admin.password_hash):
        record_login_failure(session, rate_limit_key)
        raise APIError(400, "current_password_incorrect", "Current password is incorrect")
    if new_password != confirmation:
        raise APIError(400, "password_mismatch", "New password and confirmation do not match")
    if not 12 <= len(new_password) <= 1024:
        raise APIError(
            400,
            "invalid_password_length",
            "New password must contain 12-1024 characters",
        )
    if verify_password(new_password, admin.password_hash):
        raise APIError(
            400,
            "password_unchanged",
            "New password must differ from the current password",
        )

    try:
        locked_admin = session.scalar(
            select(Admin)
            .where(Admin.admin_id == admin.admin_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            locked_admin is None
            or not locked_admin.is_active
            or not verify_password(current_password, locked_admin.password_hash)
        ):
            record_login_failure(session, rate_limit_key)
            raise APIError(400, "current_password_incorrect", "Current password is incorrect")

        locked_admin.password_hash = hash_password(new_password)
        locked_admin.auth_version += 1
        session.add(
            AuditLog(
                actor_admin_id=locked_admin.admin_id,
                action="admin_password_changed",
                target_type="admin",
                target_id=locked_admin.admin_id,
                outcome="success",
                metadata_={},
            )
        )
        reset_login_rate_limit(session, rate_limit_key)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise

    return ChangePasswordResponse(
        message="Password changed. Sign in again with your new password.",
        reauthenticate=True,
    )


@router.get("/me", response_model=AdminPublic, summary="Get the authenticated Admin")
def current_admin(admin: Admin = Depends(get_current_admin)) -> AdminPublic:
    return AdminPublic.model_validate(admin)
