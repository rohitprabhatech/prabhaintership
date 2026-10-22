from sqlalchemy import MetaData
from sqlalchemy.dialects.mysql import dialect as mysql_dialect
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

DATABASE_SCHEMA = get_settings().db_name


def mysql_qualified_name(name: str) -> str:
    preparer = mysql_dialect().identifier_preparer
    return f"{preparer.quote_identifier(DATABASE_SCHEMA)}.{preparer.quote_identifier(name)}"


class Base(DeclarativeBase):
    metadata = MetaData(schema=DATABASE_SCHEMA)