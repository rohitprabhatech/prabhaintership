from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.batch import Batch


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
        statement = select(Batch)
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
        rows = self.session.scalars(
            statement.order_by(Batch.starts_on.desc(), Batch.batch_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total
