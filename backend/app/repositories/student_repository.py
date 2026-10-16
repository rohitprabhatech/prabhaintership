from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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