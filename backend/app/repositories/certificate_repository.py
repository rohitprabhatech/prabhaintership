from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import mysql_qualified_name
from app.models.certificate import Certificate
from app.models.certificate_event import CertificateEvent


class CertificateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, certificate_id: int, *, lock: bool = False) -> Certificate | None:
        from sqlalchemy import select

        statement = select(Certificate).where(Certificate.certificate_id == certificate_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_by_number(self, certificate_number: str) -> Certificate | None:
        from sqlalchemy import select

        statement = select(Certificate).where(Certificate.certificate_number == certificate_number)
        return self.session.scalar(statement)

    def status_row(self, certificate_id: int) -> dict | None:
        row = (
            self.session.execute(
                text(
                    "SELECT cs.certificate_id, cs.enrollment_id, cs.certificate_number, "
                    "cs.certificate_type, cs.issued_at, cs.created_at, cs.document_uri, "
                    "cs.replaces_certificate_id, cs.issued_by, cs.derived_status, "
                    "cs.terminal_event_at, e.enrollment_number, s.student_number, s.full_name, "
                    f"p.program_code FROM {mysql_qualified_name('v_certificate_status')} cs "
                    f"JOIN {mysql_qualified_name('enrollments')} e "
                    "ON e.enrollment_id = cs.enrollment_id "
                    f"JOIN {mysql_qualified_name('students')} s ON s.student_id = e.student_id "
                    f"JOIN {mysql_qualified_name('internship_programs')} p "
                    "ON p.program_id = e.program_id "
                    "WHERE cs.certificate_id = :certificate_id"
                ),
                {"certificate_id": certificate_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def list_report(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        enrollment_id: int | None,
        search: str | None,
    ):
        where = []
        params: dict[str, object] = {
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }
        if status is not None:
            where.append("cs.derived_status = :status")
            params["status"] = status
        if enrollment_id is not None:
            where.append("cs.enrollment_id = :enrollment_id")
            params["enrollment_id"] = enrollment_id
        if search:
            where.append(
                "(cs.certificate_number ILIKE :search ESCAPE '!' "
                "OR e.enrollment_number ILIKE :search ESCAPE '!' "
                "OR s.student_number ILIKE :search ESCAPE '!' "
                "OR s.full_name ILIKE :search ESCAPE '!')"
            )
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            params["search"] = f"%{escaped}%"
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        from_sql = (
            f" FROM {mysql_qualified_name('v_certificate_status')} cs "
            f"JOIN {mysql_qualified_name('enrollments')} e ON e.enrollment_id = cs.enrollment_id "
            f"JOIN {mysql_qualified_name('students')} s ON s.student_id = e.student_id "
            f"JOIN {mysql_qualified_name('internship_programs')} p ON p.program_id = e.program_id "
        )
        count = self.session.execute(
            text("SELECT count(*)" + from_sql + where_sql), params
        ).scalar_one()
        rows = (
            self.session.execute(
                text(
                    "SELECT cs.certificate_id, cs.enrollment_id, cs.certificate_number, "
                    "cs.certificate_type, cs.issued_at, cs.created_at, cs.document_uri, "
                    "cs.replaces_certificate_id, cs.issued_by, cs.derived_status, "
                    "cs.terminal_event_at, e.enrollment_number, s.student_number, s.full_name, "
                    "p.program_code"
                    + from_sql
                    + where_sql
                    + " ORDER BY cs.issued_at DESC, cs.certificate_id DESC "
                    + "LIMIT :limit OFFSET :offset"
                ),
                params,
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows], count

    def events(self, certificate_id: int) -> list[CertificateEvent]:
        from sqlalchemy import select

        return list(
            self.session.scalars(
                select(CertificateEvent)
                .where(CertificateEvent.certificate_id == certificate_id)
                .order_by(CertificateEvent.occurred_at, CertificateEvent.certificate_event_id)
            ).all()
        )
