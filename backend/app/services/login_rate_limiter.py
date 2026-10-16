from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.admin_login_throttle import AdminLoginThrottle


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0


def check_login_rate_limit(session: Session, key_hash: str) -> RateLimitDecision:
    settings = get_settings()
    now = datetime.now(UTC)
    retention_seconds = max(
        86400,
        settings.auth_rate_limit_window_seconds + settings.auth_rate_limit_block_seconds,
    )
    session.execute(
        delete(AdminLoginThrottle).where(
            AdminLoginThrottle.updated_at < now - timedelta(seconds=retention_seconds)
        )
    )
    session.execute(
        insert(AdminLoginThrottle)
        .values(client_key_hash=key_hash, window_started_at=now, failure_count=0, updated_at=now)
        .on_conflict_do_nothing(index_elements=[AdminLoginThrottle.client_key_hash])
    )
    bucket = session.scalar(
        select(AdminLoginThrottle)
        .where(AdminLoginThrottle.client_key_hash == key_hash)
        .with_for_update()
    )
    if bucket is None:
        raise RuntimeError("Login throttle bucket could not be created")

    if bucket.blocked_until is not None:
        if bucket.blocked_until > now:
            retry_after = max(1, int((bucket.blocked_until - now).total_seconds()))
            session.rollback()
            return RateLimitDecision(False, retry_after)
        bucket.blocked_until = None
        bucket.failure_count = 0
        bucket.window_started_at = now
    elif now - bucket.window_started_at >= timedelta(
        seconds=settings.auth_rate_limit_window_seconds
    ):
        bucket.failure_count = 0
        bucket.window_started_at = now

    bucket.updated_at = now
    if bucket.failure_count >= settings.auth_rate_limit_attempts:
        bucket.blocked_until = now + timedelta(seconds=settings.auth_rate_limit_block_seconds)
        retry_after = settings.auth_rate_limit_block_seconds
        session.commit()
        return RateLimitDecision(False, retry_after)
    return RateLimitDecision(True)


def record_login_failure(session: Session, key_hash: str) -> None:
    settings = get_settings()
    bucket = session.scalar(
        select(AdminLoginThrottle)
        .where(AdminLoginThrottle.client_key_hash == key_hash)
        .with_for_update()
    )
    if bucket is None:
        raise RuntimeError("Login throttle bucket disappeared")

    now = datetime.now(UTC)
    bucket.failure_count += 1
    bucket.updated_at = now
    if bucket.failure_count >= settings.auth_rate_limit_attempts:
        bucket.blocked_until = now + timedelta(seconds=settings.auth_rate_limit_block_seconds)
    session.commit()


def reset_login_rate_limit(session: Session, key_hash: str) -> None:
    bucket = session.get(AdminLoginThrottle, key_hash)
    if bucket is not None:
        session.delete(bucket)
        session.commit()