from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.enrollment import Enrollment
from app.models.enrollment_fee_term import EnrollmentFeeTerm
from app.models.fee_adjustment import FeeAdjustment
from app.models.payment import Payment
from app.models.payment_adjustment import PaymentAdjustment
from app.models.project_assignment import ProjectAssignment
from app.models.student import Student
from app.repositories.batch_repository import BatchRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.program_repository import ProgramRepository
from app.schemas.enrollment import EnrollmentCreate, EnrollmentPage
from app.schemas.lifecycle import DependencySummary
from app.services.business_number_service import generate_business_number
from app.services.lifecycle import audit_lifecycle_action

_ENROLLMENT_TRANSITIONS = {
    "active": {"completed", "withdrawn", "cancelled"},
    "completed": set(),
    "withdrawn": set(),
    "cancelled": set(),
}


def create_enrollment(session: Session, payload: EnrollmentCreate, admin_id: int) -> Enrollment:
    repository = EnrollmentRepository(session)

    student = session.scalar(
        select(Student).where(Student.student_id == payload.student_id).with_for_update()
    )
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")
    if student.status != "active":
        raise APIError(409, "student_not_active", "Only active students can be enrolled")

    batch = BatchRepository(session).get(payload.batch_id, lock=True)
    if batch is None:
        raise APIError(404, "batch_not_found", "Batch was not found")
    program = ProgramRepository(session).get(batch.program_id, lock=True)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    if program.status != "active":
        raise APIError(409, "program_not_active", "Only active programs accept enrollments")

    if batch.status not in {"planned", "active"}:
        raise APIError(409, "batch_not_open", "This batch does not accept enrollments")
    if payload.starts_on < batch.starts_on or payload.starts_on > batch.ends_on:
        raise APIError(
            422, "enrollment_outside_batch_dates", "Enrollment start must be within batch dates"
        )
    if payload.ends_on is not None and payload.ends_on > batch.ends_on:
        raise APIError(
            422, "enrollment_outside_batch_dates", "Enrollment end must be within batch dates"
        )
    if (
        batch.capacity is not None
        and repository.active_count_for_batch(batch.batch_id) >= batch.capacity
    ):
        raise APIError(409, "batch_capacity_reached", "Batch capacity has been reached")

    if repository.active_duplicate(
        student_id=student.student_id,
        program_id=program.program_id,
        batch_id=batch.batch_id,
    ):
        raise APIError(
            409,
            "duplicate_active_enrollment",
            "Student already has an active enrollment for this program and batch",
        )

    enrollment_values = payload.model_dump(exclude={"agreed_fee_amount", "fee_reason"})
    enrollment = Enrollment(
        **enrollment_values,
        enrollment_number=generate_business_number(session, "enrollment"),
        program_id=program.program_id,
        status="active",
        created_by=admin_id,
    )
    session.add(enrollment)
    try:
        session.flush()
        session.add(
            EnrollmentFeeTerm(
                enrollment_id=enrollment.enrollment_id,
                agreed_amount=payload.agreed_fee_amount,
                reason=payload.fee_reason,
                created_by=admin_id,
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "enrollment_conflict",
            "Enrollment conflicts with an existing record or violates a database constraint",
        ) from None
    session.refresh(enrollment)
    return enrollment


def list_enrollments(
    session: Session,
    *,
    page: int,
    page_size: int,
    student_id: int | None,
    program_id: int | None,
    batch_id: int | None,
    status: str | None,
    search: str | None,
) -> EnrollmentPage:
    rows, total = EnrollmentRepository(session).list(
        page=page,
        page_size=page_size,
        student_id=student_id,
        program_id=program_id,
        batch_id=batch_id,
        status=status,
        search=search.strip() if search else None,
    )
    return EnrollmentPage(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_enrollment(session: Session, enrollment_id: int) -> Enrollment:
    enrollment = EnrollmentRepository(session).get(enrollment_id)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    return enrollment


def update_enrollment_status(
    session: Session,
    enrollment_id: int,
    requested_status: str,
    reason: str | None,
    admin_id: int,
    request_id=None,
) -> Enrollment:
    repository = EnrollmentRepository(session)
    enrollment = repository.get(enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    if requested_status == enrollment.status:
        return enrollment
    if requested_status not in _ENROLLMENT_TRANSITIONS[enrollment.status]:
        raise APIError(
            409,
            "invalid_enrollment_status_transition",
            "Enrollment status transition is not allowed",
        )

    previous_status = enrollment.status
    enrollment.status = requested_status
    if requested_status in {"cancelled", "withdrawn"}:
        audit_lifecycle_action(
            session,
            admin_id=admin_id,
            action=f"enrollment_{requested_status}",
            target_type="enrollment",
            target_id=enrollment_id,
            reason=reason or f"Enrollment status changed to {requested_status}",
            request_id=request_id,
            metadata={
                "enrollment_number": enrollment.enrollment_number,
                "status_before": previous_status,
            },
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "enrollment_conflict", "Enrollment status conflicts with another record"
        ) from None
    session.refresh(enrollment)
    return enrollment


def enrollment_dependencies(session: Session, enrollment_id: int) -> DependencySummary:
    enrollment = get_enrollment(session, enrollment_id)
    dependencies = {
        "fee_terms": session.scalar(
            select(func.count())
            .select_from(EnrollmentFeeTerm)
            .where(EnrollmentFeeTerm.enrollment_id == enrollment_id)
        )
        or 0,
        "fee_adjustments": session.scalar(
            select(func.count())
            .select_from(FeeAdjustment)
            .where(FeeAdjustment.enrollment_id == enrollment_id)
        )
        or 0,
        "payments": session.scalar(
            select(func.count()).select_from(Payment).where(Payment.enrollment_id == enrollment_id)
        )
        or 0,
        "project_assignments": session.scalar(
            select(func.count())
            .select_from(ProjectAssignment)
            .where(ProjectAssignment.enrollment_id == enrollment_id)
        )
        or 0,
        "certificates": session.scalar(
            select(func.count())
            .select_from(Certificate)
            .where(Certificate.enrollment_id == enrollment_id)
        )
        or 0,
    }
    dependencies["payment_adjustments"] = session.scalar(
        select(func.count())
        .select_from(PaymentAdjustment)
        .join(Payment, Payment.payment_id == PaymentAdjustment.payment_id)
        .where(Payment.enrollment_id == enrollment_id)
    ) or 0
    return DependencySummary(
        resource="enrollment",
        identifier=enrollment.enrollment_number,
        dependencies=dependencies,
        can_delete=not any(dependencies.values()),
    )


def delete_enrollment(
    session: Session,
    enrollment_id: int,
    reason: str,
    admin_id: int,
    request_id=None,
) -> None:
    enrollment = EnrollmentRepository(session).get(enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    dependencies = enrollment_dependencies(session, enrollment_id)
    if not dependencies.can_delete:
        raise APIError(
            409,
            "enrollment_has_history",
            (
                "Enrollment cannot be permanently deleted while financial, project, or "
                "certificate history references it. Cancel or withdraw it instead."
            ),
        )
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="enrollment_deleted",
            target_type="enrollment",
            target_id=enrollment_id,
            request_id=request_id,
            metadata_={"enrollment_number": enrollment.enrollment_number, "reason": reason},
        )
    )
    session.delete(enrollment)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "enrollment_delete_conflict",
            (
                "Enrollment is referenced by historical records and cannot be deleted. "
                "Cancel or withdraw it instead."
            ),
        ) from None
