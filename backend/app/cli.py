import argparse
import getpass
import logging
import sys

from sqlalchemy import create_engine, func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db.base import mysql_qualified_name
from app.db.session import get_admin_provisioning_session_factory, get_session_factory
from app.errors import APIError
from app.logging_config import configure_logging
from app.models.admin import Admin
from app.services.admin_provisioning import (
    bootstrap_admin,
    normalize_admin_email,
    normalize_admin_username,
    replace_admin_accounts,
    reset_admin_password,
)
from app.services.auth_service import authenticate_admin


def prompt_password() -> tuple[str, str]:
    password = getpass.getpass("New Admin password: ")
    confirmation = getpass.getpass("Confirm Admin password: ")
    return password, confirmation


def run_bootstrap(username: str, email: str | None) -> None:
    configure_logging()
    password, confirmation = prompt_password()
    try:
        with get_admin_provisioning_session_factory()() as session:
            bootstrap_admin(session, username, email, password, confirmation)
    except APIError as exc:
        raise SystemExit(exc.message) from None
    logging.getLogger("app.cli").info(
        "Admin bootstrap completed", extra={"event": "admin_bootstrapped"}
    )


def run_password_reset(username: str) -> None:
    configure_logging()
    password, confirmation = prompt_password()
    try:
        with get_admin_provisioning_session_factory()() as session:
            reset_admin_password(session, username, password, confirmation)
    except APIError as exc:
        raise SystemExit(exc.message) from None
    logging.getLogger("app.cli").info(
        "Admin password reset completed; previous access tokens revoked",
        extra={"event": "admin_password_reset"},
    )


def run_admin_replacement(username: str, email: str) -> None:
    configure_logging()
    try:
        normalized_username = normalize_admin_username(username)
        normalized_email = normalize_admin_email(email)
    except APIError as exc:
        raise SystemExit(exc.message) from None
    session_factory = get_admin_provisioning_session_factory()
    app_settings = get_settings()
    app_engine = create_engine(
        app_settings.database_url,
        connect_args=app_settings.database_connect_args,
        pool_pre_ping=True,
    )

    try:
        with app_engine.connect() as connection:
            app_database_identity = connection.execute(
                text("SELECT DATABASE(), @@hostname, @@port")
            ).one()
        with session_factory() as session:
            provisioning_database_identity = session.execute(
                text("SELECT DATABASE(), @@hostname, @@port")
            ).one()
            total_admins = session.scalar(select(func.count(Admin.admin_id))) or 0
            active_admins = session.scalar(
                select(func.count(Admin.admin_id)).where(Admin.is_active.is_(True))
            ) or 0
            identity_exists = session.scalar(
                select(Admin.admin_id).where(
                    or_(
                        Admin.username == normalized_username,
                        Admin.email_normalized == normalized_email,
                    )
                )
            )
            session.rollback()
    except SQLAlchemyError:
        raise SystemExit(
            "Admin replacement preflight failed; no account records were changed"
        ) from None
    finally:
        app_engine.dispose()

    if app_database_identity != provisioning_database_identity:
        raise SystemExit(
            "Application and provisioning databases do not match; no account records were changed"
        )

    if active_admins < 1:
        raise SystemExit(
            "Admin replacement requires at least one active Admin; inspect the database "
            "before retrying"
        )
    if identity_exists is not None:
        raise SystemExit(
            "The requested Admin username or email already exists; no account records were changed"
        )

    confirmation_phrase = (
        f"DEACTIVATE ALL {active_admins} ACTIVE ADMINS AND CREATE "
        f"{normalized_username.upper()}"
    )
    print(f"Database: {provisioning_database_identity[0]}")
    print(f"Replacement target: {normalized_username} / {normalized_email}")
    print(f"Existing active Admin accounts to deactivate: {active_admins}")
    print(f"Existing inactive Admin accounts to retain: {total_admins - active_admins}")
    print("Existing Admin rows and their audit/business references will be retained.")
    if input(f"Type exactly '{confirmation_phrase}' to continue: ") != confirmation_phrase:
        raise SystemExit("Confirmation did not match; no account records were changed")

    password, password_confirmation = prompt_password()
    try:
        with session_factory() as session:
            _, deactivated_count = replace_admin_accounts(
                session,
                normalized_username,
                normalized_email,
                password,
                password_confirmation,
                active_admins,
                confirmation_phrase,
            )
    except APIError as exc:
        raise SystemExit(exc.message) from None
    except SQLAlchemyError:
        raise SystemExit(
            "Admin replacement transaction failed; inspect the database before retrying"
        ) from None

    try:
        with get_session_factory()() as session:
            authenticated = authenticate_admin(session, normalized_username, password)
            if (
                authenticated is None
                or authenticated.email != normalized_email
                or not authenticated.is_active
            ):
                raise RuntimeError("Replacement Admin authentication verification failed")
    except SQLAlchemyError:
        raise SystemExit(
            "Replacement committed, but application-database authentication verification "
            "failed; do not rerun replacement and inspect the account read-only"
        ) from None
    except RuntimeError as exc:
        raise SystemExit(
            f"{exc}; do not rerun replacement and inspect the account read-only"
        ) from None

    print(
        f"Admin replacement verified: {normalized_username} / {normalized_email}; "
        f"active account; {deactivated_count} previous Admin accounts deactivated."
    )


def run_database_verification() -> int:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args=settings.database_connect_args,
    )
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT 1")) != 1:
                raise RuntimeError("Connectivity query returned an unexpected result")
            database_name, server_version = connection.execute(
                text("SELECT DATABASE(), VERSION()")
            ).one()
            admin_count = connection.scalar(
                text(f"SELECT COUNT(*) FROM {mysql_qualified_name('admins')}")
            )
        print("MySQL connection: successful")
        print(f"Database: {database_name}")
        print(f"MySQL server version: {server_version}")
        print(f"Admin accounts: {admin_count}")
        return 0
    except SQLAlchemyError as error:
        original = getattr(error, "orig", None)
        code = (
            original.args[0]
            if original is not None and getattr(original, "args", None)
            else None
        )
        categories = {
            1045: "access denied",
            1049: "database not found",
            2003: "MySQL server unreachable",
            2005: "MySQL host could not be resolved",
        }
        category = categories.get(code, "database connection/query failed")
        suffix = f" (MySQL error {code})" if code is not None else ""
        print(f"MySQL verification failed: {category}{suffix}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"MySQL verification failed: {error}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Internal Admin account provisioning")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = subparsers.add_parser("bootstrap-admin")
    bootstrap_parser.add_argument("--username", required=True)
    bootstrap_parser.add_argument("--email")
    reset_parser = subparsers.add_parser("reset-admin-password")
    reset_parser.add_argument("--username", required=True)
    replace_parser = subparsers.add_parser("replace-admin")
    replace_parser.add_argument("--username", required=True)
    replace_parser.add_argument("--email", required=True)
    subparsers.add_parser("verify-db")
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        run_bootstrap(args.username, args.email)
    elif args.command == "reset-admin-password":
        run_password_reset(args.username)
    elif args.command == "replace-admin":
        run_admin_replacement(args.username, args.email)
    elif args.command == "verify-db":
        raise SystemExit(run_database_verification())


if __name__ == "__main__":
    main()
