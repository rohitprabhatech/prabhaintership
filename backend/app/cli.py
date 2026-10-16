import argparse
import getpass
import logging

from app.db.session import get_admin_provisioning_session_factory
from app.errors import APIError
from app.logging_config import configure_logging
from app.services.admin_provisioning import bootstrap_admin, reset_admin_password


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Internal Admin account provisioning")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = subparsers.add_parser("bootstrap-admin")
    bootstrap_parser.add_argument("--username", required=True)
    bootstrap_parser.add_argument("--email")
    reset_parser = subparsers.add_parser("reset-admin-password")
    reset_parser.add_argument("--username", required=True)
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        run_bootstrap(args.username, args.email)
    elif args.command == "reset-admin-password":
        run_password_reset(args.username)


if __name__ == "__main__":
    main()
