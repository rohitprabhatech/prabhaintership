from __future__ import annotations

from sqlalchemy import bindparam, func, or_, select, text
from sqlalchemy.orm import Session

from app.db.base import mysql_qualified_name
from app.models.batch import Batch
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.internship_program import InternshipProgram


class BatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, batch_id: int, *, lock: bool = False) -> Batch | None:
        statement = select(Batch).where(Batch.batch_id == batch_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_by_code(self, program_id: int, batch_code: str, *, exclude_id: int | None = None):
        statement = select(Batch).where(
            Batch.program_id == program_id,
            func.lower(Batch.batch_code) == batch_code.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(Batch.batch_id != exclude_id)
        return self.session.scalar(statement)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        program_id: int | None,
        status: str | None,
    ):
        enrollment_count = (
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.batch_id == Batch.batch_id,
                Enrollment.program_id == Batch.program_id,
            )
            .correlate(Batch)
            .scalar_subquery()
        )
        active_enrollment_count = (
            select(func.count())
            .select_from(Enrollment)
            .where(
                Enrollment.batch_id == Batch.batch_id,
                Enrollment.program_id == Batch.program_id,
                Enrollment.status == "active",
            )
            .correlate(Batch)
            .scalar_subquery()
        )
        unique_active_student_count = (
            select(func.count(func.distinct(Enrollment.student_id)))
            .select_from(Enrollment)
            .where(
                Enrollment.batch_id == Batch.batch_id,
                Enrollment.program_id == Batch.program_id,
                Enrollment.status == "active",
            )
            .correlate(Batch)
            .scalar_subquery()
        )
        statement = (
            select(
                Batch,
                InternshipProgram.name,
                InternshipProgram.program_code,
                enrollment_count,
                active_enrollment_count,
                unique_active_student_count,
            )
            .outerjoin(InternshipProgram, InternshipProgram.program_id == Batch.program_id)
        )
        count_statement = select(func.count()).select_from(Batch)
        filters = []
        if program_id is not None:
            filters.append(Batch.program_id == program_id)
        if status is not None:
            filters.append(Batch.status == status)
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.execute(
            statement.order_by(Batch.starts_on.desc(), Batch.batch_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return rows, total

    def roster_page(
        self,
        batch_id: int,
        *,
        page: int,
        page_size: int,
        search: str | None,
        enrollment_status: str | None,
    ):
        statement = (
            select(Enrollment, Student)
            .join(Student, Student.student_id == Enrollment.student_id)
            .where(Enrollment.batch_id == batch_id)
        )
        count_statement = (
            select(func.count(func.distinct(Enrollment.enrollment_id)))
            .select_from(Enrollment)
            .join(Student, Student.student_id == Enrollment.student_id)
            .where(Enrollment.batch_id == batch_id)
        )
        filters = []
        if enrollment_status is not None:
            filters.append(Enrollment.status == enrollment_status)
        if search:
            escaped = _escape_like(search)
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Enrollment.enrollment_number.ilike(pattern, escape="\\"),
                    Student.student_number.ilike(pattern, escape="\\"),
                    Student.full_name.ilike(pattern, escape="\\"),
                    Student.email.ilike(pattern, escape="\\"),
                    Student.phone.ilike(pattern, escape="\\"),
                )
            )
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.execute(
            statement.order_by(func.lower(Student.full_name), Student.student_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        enrollment_count = self.session.scalar(
            select(func.count()).select_from(Enrollment).where(Enrollment.batch_id == batch_id)
        ) or 0
        active_enrollment_count = self.session.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.batch_id == batch_id, Enrollment.status == "active")
        ) or 0
        unique_active_student_count = self.session.scalar(
            select(func.count(func.distinct(Enrollment.student_id)))
            .select_from(Enrollment)
            .where(Enrollment.batch_id == batch_id, Enrollment.status == "active")
        ) or 0
        return (
            rows,
            total,
            enrollment_count,
            active_enrollment_count,
            unique_active_student_count,
        )

    def fee_summaries(self, enrollment_ids: list[int]) -> dict[int, dict]:
        if not enrollment_ids:
            return {}
        statement = text(
            "SELECT enrollment_id, effective_fee, net_paid, pending_balance, currency "
            f"FROM {mysql_qualified_name('v_enrollment_balances')} "
            "WHERE enrollment_id IN :enrollment_ids"
        ).bindparams(bindparam("enrollment_ids", expanding=True))
        rows = self.session.execute(statement, {"enrollment_ids": enrollment_ids}).mappings()
        return {row["enrollment_id"]: dict(row) for row in rows}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
