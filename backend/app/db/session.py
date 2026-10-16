from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_admin_provisioning_settings, get_settings


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        get_settings().database_url,
        connect_args=get_settings().database_connect_args,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@lru_cache
def get_admin_provisioning_session_factory() -> sessionmaker[Session]:
    database_url = get_admin_provisioning_settings().database_url
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session
