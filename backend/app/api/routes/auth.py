import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.errors import APIError
from app.models.admin import Admin
from app.models.audit_log import AuditLog
from app.schemas.auth import AdminPublic, LoginRequest, LoginResponse
from app.security import client_rate_limit_key, create_access_token
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


@router.get("/me", response_model=AdminPublic, summary="Get the authenticated Admin")
def current_admin(admin: Admin = Depends(get_current_admin)) -> AdminPublic:
    return AdminPublic.model_validate(admin)
