import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.errors import APIError
from app.models.admin import Admin
from app.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> Admin:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise APIError(401, "authentication_required", "Authentication is required")
    try:
        admin_id, auth_version = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise APIError(401, "invalid_token", "The access token is invalid or expired") from None

    admin = session.scalar(select(Admin).where(Admin.admin_id == admin_id))
    if admin is None or not admin.is_active or admin.auth_version != auth_version:
        raise APIError(401, "invalid_token", "The access token is invalid or expired")
    return admin