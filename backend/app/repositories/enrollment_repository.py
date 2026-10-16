from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.student import Student


class EnrollmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, enrollment_id: int, *, lock: bool = False) -> Enrollment | None:
        statement = select(Enrollment).where(Enrollment.enrollment_id == enrollment_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_by_number(self, enrollment_number: str) -> Enrollment | None:
        return self.session.scalar(
            select(Enrollment).where(
                func.lower(Enrollment.enrollment_number) == enrollment_number.lower()
            )
        )

    def active_duplicate(
        self,
        *,
        student_id: int,
        program_id: int,
        batch_id: int | None,
        exclude_id: int | None = None,
    ) -> Enrollment | None:
        statement = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.program_id == program_id,
            Enrollment.batch_id.is_(None) if batch_id is None else Enrollment.batch_id == batch_id,
            Enrollment.status == "active",
        )
        if exclude_id is not None:
            statement = statement.where(Enrollment.enrollment_id != exclude_id)
        return self.session.scalar(statement)

    def active_count_for_batch(self, batch_id: int) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(Enrollment)
                .where(Enrollment.batch_id == batch_id, Enrollment.status == "active")
            )
            or 0
        )

    def dates_within_batch(self, batch_id: int) -> list[Enrollment]:
        return list(
            self.session.scalars(select(Enrollment).where(Enrollment.batch_id == batch_id)).all()
        )

    def list(
        self,
        *,
        page: int,
        page_size: int,
        student_id: int | None,
        program_id: int | None,
        batch_id: int | None,
        status: str | None,
        search: str | None,
    ):
        statement = select(Enrollment)
        count_statement = select(func.count()).select_from(Enrollment)
        filters = []
        if student_id is not None:
            filters.append(Enrollment.student_id == student_id)
        if program_id is not None:
            filters.append(Enrollment.program_id == program_id)
        if batch_id is not None:
            filters.append(Enrollment.batch_id == batch_id)
        if status is not None:
            filters.append(Enrollment.status == status)
        if search:
            pattern = f"%{_escape_like(search)}%"
            filters.append(
                or_(
                    Enrollment.enrollment_number.ilike(pattern, escape="\\"),
                    Student.student_number.ilike(pattern, escape="\\"),
                    Student.full_name.ilike(pattern, escape="\\"),
                )
            )
            statement = statement.join(Student, Student.student_id == Enrollment.student_id)
            count_statement = count_statement.join(
                Student, Student.student_id == Enrollment.student_id
            )
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.scalars(
            statement.order_by(Enrollment.created_at.desc(), Enrollment.enrollment_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def batch_roster(self, batch_id: int):
        return self.session.execute(
            select(Enrollment, Student)
            .join(Student, Student.student_id == Enrollment.student_id)
            .where(Enrollment.batch_id == batch_id)
            .order_by(func.lower(Student.full_name), Student.student_id)
        ).all()


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
