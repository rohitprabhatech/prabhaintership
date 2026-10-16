from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.internship_program import InternshipProgram


class ProgramRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, program_id: int, *, lock: bool = False) -> InternshipProgram | None:
        statement = select(InternshipProgram).where(InternshipProgram.program_id == program_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def find_by_code(self, program_code: str, *, exclude_id: int | None = None):
        statement = select(InternshipProgram).where(
            func.lower(InternshipProgram.program_code) == program_code.lower()
        )
        if exclude_id is not None:
            statement = statement.where(InternshipProgram.program_id != exclude_id)
        return self.session.scalar(statement)

    def list(self, *, page: int, page_size: int, search: str | None, status: str | None):
        statement = select(InternshipProgram)
        count_statement = select(func.count()).select_from(InternshipProgram)
        filters = []
        if status is not None:
            filters.append(InternshipProgram.status == status)
        if search:
            pattern = f"%{_escape_like(search)}%"
            filters.append(
                or_(
                    InternshipProgram.program_code.ilike(pattern, escape="\\"),
                    InternshipProgram.name.ilike(pattern, escape="\\"),
                )
            )
        if filters:
            statement = statement.where(*filters)
            count_statement = count_statement.where(*filters)
        total = self.session.scalar(count_statement) or 0
        rows = self.session.scalars(
            statement.order_by(func.lower(InternshipProgram.name), InternshipProgram.program_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
