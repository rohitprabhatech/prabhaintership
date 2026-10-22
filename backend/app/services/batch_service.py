from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.batch import Batch
from app.models.enrollment import Enrollment
from app.repositories.batch_repository import BatchRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.program_repository import ProgramRepository
from app.schemas.batch import BatchCreate, BatchListItem, BatchPage, BatchResponse, BatchUpdate
from app.schemas.enrollment import BatchRosterPage, BatchStudentRow
from app.schemas.lifecycle import DependencySummary
from app.services.business_number_service import generate_business_number
from app.services.lifecycle import audit_lifecycle_action

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
    batch = Batch(
        **payload.model_dump(),
        batch_code=generate_business_number(session, "batch"),
        created_by=admin_id,
    )
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
    items = []
    for (
        batch,
        program_name,
        program_code,
        enrollment_count,
        active_enrollment_count,
        unique_active_student_count,
    ) in rows:
        if program_name is None or program_code is None:
            raise APIError(
                500,
                "batch_program_integrity_error",
                "A batch references a missing internship program",
            )
        items.append(
            BatchListItem(
                **BatchResponse.model_validate(batch).model_dump(),
                program_name=program_name,
                program_code=program_code,
                enrollment_count=enrollment_count,
                active_enrollment_count=active_enrollment_count,
                unique_active_student_count=unique_active_student_count,
            )
        )
    return BatchPage(
        items=items,
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


def update_batch(
    session: Session, batch_id: int, payload: BatchUpdate, admin_id: int, request_id=None
) -> Batch:
    repository = BatchRepository(session)
    batch = repository.get(batch_id, lock=True)
    if batch is None:
        raise APIError(404, "batch_not_found", "Batch was not found")
    changes = payload.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None)
    previous_status = batch.status
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
    if previous_status != requested_status:
        audit_lifecycle_action(
            session,
            admin_id=admin_id,
            action=f"batch_{requested_status}",
            target_type="batch",
            target_id=batch_id,
            reason=reason or f"Batch status changed to {requested_status}",
            request_id=request_id,
            metadata={"batch_code": batch.batch_code, "status_before": previous_status},
        )
    return _commit(session, batch, "batch_conflict")


def batch_dependencies(session: Session, batch_id: int) -> DependencySummary:
    batch = get_batch(session, batch_id)
    enrollments = session.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.batch_id == batch_id)
    ) or 0
    return DependencySummary(
        resource="batch",
        identifier=batch.batch_code,
        dependencies={"enrollments": enrollments},
        can_delete=enrollments == 0,
    )


def delete_batch(
    session: Session, batch_id: int, reason: str, admin_id: int, request_id=None
) -> None:
    batch = BatchRepository(session).get(batch_id, lock=True)
    if batch is None:
        raise APIError(404, "batch_not_found", "Batch was not found")
    dependencies = batch_dependencies(session, batch_id)
    if not dependencies.can_delete:
        raise APIError(
            409,
            "batch_has_history",
            (
                "Batch cannot be permanently deleted while enrollments reference it. "
                "Cancel it instead."
            ),
        )
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="batch_deleted",
            target_type="batch",
            target_id=batch_id,
            request_id=request_id,
            metadata_={"batch_code": batch.batch_code, "reason": reason},
        )
    )
    session.delete(batch)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "batch_delete_conflict",
            "Batch is referenced by historical records and cannot be deleted. Cancel it instead.",
        ) from None


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


def get_batch_students(
    session: Session,
    batch_id: int,
    *,
    page: int,
    page_size: int,
    search: str | None,
    enrollment_status: str | None,
) -> BatchRosterPage:
    batch = get_batch(session, batch_id)
    repository = BatchRepository(session)
    rows, total, enrollment_count, active_count, unique_active_count = repository.roster_page(
        batch_id,
        page=page,
        page_size=page_size,
        search=search.strip() if search else None,
        enrollment_status=enrollment_status,
    )
    fee_summaries = repository.fee_summaries(
        [enrollment.enrollment_id for enrollment, _student in rows]
    )
    students = []
    for enrollment, student in rows:
        fee_values = fee_summaries.get(enrollment.enrollment_id)
        students.append(
            BatchStudentRow(
                enrollment_id=enrollment.enrollment_id,
                enrollment_number=enrollment.enrollment_number,
                enrollment_status=enrollment.status,
                enrollment_starts_on=enrollment.starts_on,
                enrollment_ends_on=enrollment.ends_on,
                student_id=student.student_id,
                student_number=student.student_number,
                full_name=student.full_name,
                email=student.email,
                phone=student.phone,
                fee_summary=fee_values,
            )
        )
    return BatchRosterPage(
        batch_id=batch.batch_id,
        program_id=batch.program_id,
        batch_code=batch.batch_code,
        name=batch.name,
        starts_on=batch.starts_on,
        ends_on=batch.ends_on,
        capacity=batch.capacity,
        enrollment_count=enrollment_count,
        active_enrollment_count=active_count,
        unique_active_student_count=unique_active_count,
        students=students,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def _commit(session: Session, batch: Batch, code: str) -> Batch:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(409, code, "Batch conflicts with an existing record") from None
    session.refresh(batch)
    return batch
