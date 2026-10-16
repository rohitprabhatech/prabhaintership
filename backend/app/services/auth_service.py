from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import Admin
from app.security import verify_password, verify_unknown_user_password


def authenticate_admin(session: Session, username: str, password: str) -> Admin | None:
    normalized_username = username.strip().lower()
    admin = session.scalar(select(Admin).where(Admin.username == normalized_username))
    if admin is None:
        verify_unknown_user_password(password)
        return None
    if not verify_password(password, admin.password_hash) or not admin.is_active:
        return None
    admin.last_login_at = datetime.now(UTC)
    session.commit()
    session.refresh(admin)
    return admin