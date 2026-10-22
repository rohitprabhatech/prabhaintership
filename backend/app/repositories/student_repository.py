from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.orm import Session

from app.db.base import mysql_qualified_name
from app.models.enrollment import Enrollment
from app.models.student import Student


class StudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, student_id: int) -> Student | None:
        return self.session.get(Student, student_id)

    def find_by_number(
        self, student_number: str, *, exclude_id: int | None = None
    ) -> Student | None:
        statement = select(Student).where(Student.student_number == student_number)
        if exclude_id is not None:
            statement = statement.where(Student.student_id != exclude_id)
        return self.session.scalar(statement)

    def find_by_email(self, email: str, *, exclude_id: int | None = None) -> Student | None:
        statement = select(Student).where(func.lower(Student.email) == email.lower())
        if exclude_id is not None:
            statement = statement.where(Student.student_id != exclude_id)
        return self.session.scalar(statement)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None,
        program_id: int | None = None,
        batch_id: int | None = None,
        enrollment_status: str | None = None,
        fee_status: str | None = None,
    ) -> tuple[list[Student], int]:
        statement = select(Student)
        count_statement = select(func.count()).select_from(Student)
        filters = []
        if status is not None:
            filters.append(Student.status == status)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    Student.student_number.ilike(pattern, escape="\\"),
                    Student.full_name.ilike(pattern, escape="\\"),
                    Student.email.ilike(pattern, escape="\\"),
                    Student.phone.ilike(pattern, escape="\\"),
                )
            )
        if program_id is not None or batch_id is not None or enrollment_status is not None:
            enrollment_filters = [Enrollment.student_id == Student.student_id]
            if program_id is not None:
                enrollment_filters.append(Enrollment.program_id == program_id)
            if batch_id is not None:
                enrollment_filters.append(Enrollment.batch_id == batch_id)
            if enrollment_status is not None:
                enrollment_filters.append(Enrollment.status == enrollment_status)
            filters.append(
                exists(select(1).select_from(Enrollment).where(*enrollment_filters))
            )
        if fee_status is not None:
            comparison = "pending_balance > 0" if fee_status == "outstanding" else "pending_balance = 0"
            filters.append(
                text(
                    "EXISTS (SELECT 1 FROM "
                    f"{mysql_qualified_name('v_enrollment_balances')} AS balances "
                    "WHERE balances.student_id = students.student_id "
                    f"AND balances.{comparison})"
                )
            )
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)

        total = self.session.scalar(count_statement) or 0
        rows = self.session.scalars(
            statement.order_by(func.lower(Student.full_name), Student.student_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def add(self, student: Student) -> None:
        self.session.add(student)