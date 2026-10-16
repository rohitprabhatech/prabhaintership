from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.batch import Batch
from app.models.enrollment import Enrollment
from app.repositories.batch_repository import BatchRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.program_repository import ProgramRepository
from app.schemas.batch import BatchCreate, BatchPage, BatchUpdate

_BATCH_TRANSITIONS = {
    "planned": {"active", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def create_batch(session: Session, payload: BatchCreate, admin_id: int) -> Batch:
    program = ProgramRepository(session).get(payload.program_id)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    if program.status != "active":
        raise APIError(409, "program_not_active", "A batch requires an active program")
    repository = BatchRepository(session)
    if repository.find_by_code(payload.program_id, payload.batch_code):
        raise APIError(
            409, "duplicate_batch_code", "This program already has a batch with this code"
        )
    batch = Batch(**payload.model_dump(), created_by=admin_id)
    session.add(batch)
    return _commit(session, batch, "batch_conflict")


def list_batches(
    session: Session,
    *,
    page: int,
    page_size: int,
    program_id: int | None,
    status: str | None,
) -> BatchPage:
    rows, total = BatchRepository(session).list(
        page=page, page_size=page_size, program_id=program_id, status=status
    )
    return BatchPage(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_batch(session: Session, batch_id: int) -> Batch:
    batch = BatchRepository(session).get(batch_id)
    if batch is None:
        raise APIError(404, "batch_not_found", "Batch was not found")
    return batch


def update_batch(session: Session, batch_id: int, payload: BatchUpdate) -> Batch:
    repository = BatchRepository(session)
    batch = repository.get(batch_id, lock=True)
    if batch is None:
        raise APIError(404, "batch_not_found", "Batch was not found")
    changes = payload.model_dump(exclude_unset=True)
    requested_status = changes.pop("status", batch.status)
    if (
        requested_status != batch.status
        and requested_status not in _BATCH_TRANSITIONS[batch.status]
    ):
        raise APIError(
            409, "invalid_batch_status_transition", "Batch status transition is not allowed"
        )

    starts_on = changes.get("starts_on", batch.starts_on)
    ends_on = changes.get("ends_on", batch.ends_on)
    if ends_on < starts_on:
        raise APIError(422, "invalid_batch_dates", "Batch end date must not precede start date")

    capacity = changes.get("capacity", batch.capacity)
    if capacity is not None:
        active_count = EnrollmentRepository(session).active_count_for_batch(batch_id)
        if capacity < active_count:
            raise APIError(
                409,
                "batch_capacity_below_enrollment_count",
                "Capacity cannot be lower than active enrollments",
            )

    existing_enrollments = EnrollmentRepository(session).dates_within_batch(batch_id)
    for enrollment in existing_enrollments:
        if enrollment.starts_on < starts_on or enrollment.starts_on > ends_on:
            raise APIError(
                409, "batch_dates_conflict", "Batch dates cannot exclude an existing enrollment"
            )
        if enrollment.ends_on is not None and enrollment.ends_on > ends_on:
            raise APIError(
                409, "batch_dates_conflict", "Batch dates cannot exclude an existing enrollment"
            )

    for field_name, value in changes.items():
        setattr(batch, field_name, value)
    batch.status = requested_status
    return _commit(session, batch, "batch_conflict")


def get_batch_roster(session: Session, batch_id: int):
    batch = get_batch(session, batch_id)
    rows = EnrollmentRepository(session).batch_roster(batch_id)
    active_count = (
        session.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.batch_id == batch_id, Enrollment.status == "active")
        )
        or 0
    )
    return batch, rows, active_count


def _commit(session: Session, batch: Batch, code: str) -> Batch:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(409, code, "Batch conflicts with an existing record") from None
    session.refresh(batch)
    return batch
