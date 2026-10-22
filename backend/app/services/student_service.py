from datetime import UTC, datetime
from math import ceil

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.certificate_event import CertificateEvent
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
from app.repositories.student_repository import StudentRepository
from app.schemas.lifecycle import DependencySummary
from app.schemas.student import StudentActivityItem, StudentCreate, StudentPage, StudentUpdate
from app.services.business_number_service import generate_business_number
from app.services.lifecycle import audit_lifecycle_action


def list_students(
    session: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    status: str | None,
    program_id: int | None = None,
    batch_id: int | None = None,
    enrollment_status: str | None = None,
    fee_status: str | None = None,
) -> StudentPage:
    students, total = StudentRepository(session).list(
        page=page,
        page_size=page_size,
        search=search.strip() if search else None,
        status=status,
        program_id=program_id,
        batch_id=batch_id,
        enrollment_status=enrollment_status,
        fee_status=fee_status,
    )
    return StudentPage(
        items=students,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_student(session: Session, student_id: int) -> Student:
    student = StudentRepository(session).get(student_id)
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")
    return student


def student_activity(session: Session, student_id: int) -> list[StudentActivityItem]:
    student = get_student(session, student_id)
    enrollment_ids = select(Enrollment.enrollment_id).where(
        Enrollment.student_id == student.student_id
    )
    payment_ids = select(Payment.payment_id).where(Payment.enrollment_id.in_(enrollment_ids))
    certificate_ids = select(Certificate.certificate_id).where(
        Certificate.enrollment_id.in_(enrollment_ids)
    )
    target_queries = (
        ("enrollment", enrollment_ids),
        (
            "enrollment_fee_term",
            select(EnrollmentFeeTerm.fee_term_id).where(
                EnrollmentFeeTerm.enrollment_id.in_(enrollment_ids)
            ),
        ),
        (
            "fee_adjustment",
            select(FeeAdjustment.fee_adjustment_id).where(
                FeeAdjustment.enrollment_id.in_(enrollment_ids)
            ),
        ),
        ("payment", payment_ids),
        (
            "payment_adjustment",
            select(PaymentAdjustment.adjustment_id).where(
                PaymentAdjustment.payment_id.in_(payment_ids)
            ),
        ),
        (
            "project_assignment",
            select(ProjectAssignment.project_assignment_id).where(
                ProjectAssignment.enrollment_id.in_(enrollment_ids)
            ),
        ),
        ("certificate", certificate_ids),
        (
            "certificate_event",
            select(CertificateEvent.certificate_event_id).where(
                CertificateEvent.certificate_id.in_(certificate_ids)
            ),
        ),
    )
    target_filters = [
        and_(AuditLog.target_type == target_type, AuditLog.target_id.in_(target_ids))
        for target_type, target_ids in target_queries
    ]
    target_filters.append(
        and_(AuditLog.target_type == "student", AuditLog.target_id == student_id)
    )
    rows = session.scalars(
        select(AuditLog)
        .where(or_(*target_filters))
        .order_by(AuditLog.occurred_at.desc(), AuditLog.audit_log_id.desc())
        .limit(100)
    ).all()
    return [
        StudentActivityItem(
            audit_log_id=row.audit_log_id,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            outcome=row.outcome,
            occurred_at=row.occurred_at,
        )
        for row in rows
    ]


def create_student(session: Session, payload: StudentCreate, created_by: int) -> Student:
    repository = StudentRepository(session)
    email = str(payload.email).lower() if payload.email is not None else None
    _ensure_unique_email(repository, email)

    enrollment_data = None
    if payload.batch_id is not None:
        if payload.program_id is None or payload.agreed_fee_amount is None:
            raise APIError(
                422,
                "initial_enrollment_incomplete",
                "Program, batch, and agreed fee are required for an initial enrollment",
            )
        program = ProgramRepository(session).get(payload.program_id, lock=True)
        if program is None:
            raise APIError(404, "program_not_found", "Internship program was not found")
        if program.status != "active":
            raise APIError(409, "program_not_active", "Only active programs accept enrollments")
        batch = BatchRepository(session).get(payload.batch_id, lock=True)
        if batch is None:
            raise APIError(404, "batch_not_found", "Batch was not found")
        if batch.program_id != program.program_id:
            raise APIError(
                409,
                "program_batch_mismatch",
                "The selected batch does not belong to the selected program",
            )
        if batch.status not in {"planned", "active"}:
            raise APIError(409, "batch_not_open", "This batch does not accept enrollments")
        if (
            batch.capacity is not None
            and EnrollmentRepository(session).active_count_for_batch(batch.batch_id)
            >= batch.capacity
        ):
            raise APIError(409, "batch_capacity_reached", "Batch capacity has been reached")
        starts_on = payload.enrollment_starts_on or batch.starts_on
        if starts_on < batch.starts_on or starts_on > batch.ends_on:
            raise APIError(
                422,
                "enrollment_outside_batch_dates",
                "Enrollment start must be within batch dates",
            )
        enrollment_data = (program, batch, starts_on)

    student = Student(
        student_number=generate_business_number(session, "student"),
        full_name=payload.full_name,
        email=email,
        status="active",
        created_by=created_by,
        **payload.model_dump(
            exclude={
                "full_name",
                "email",
                "program_id",
                "batch_id",
                "agreed_fee_amount",
                "enrollment_starts_on",
                "fee_reason",
            }
        ),
    )
    repository.add(student)
    try:
        session.flush()
        if enrollment_data is not None:
            program, batch, starts_on = enrollment_data
            enrollment = Enrollment(
                enrollment_number=generate_business_number(session, "enrollment"),
                student_id=student.student_id,
                program_id=program.program_id,
                batch_id=batch.batch_id,
                status="active",
                starts_on=starts_on,
                created_by=created_by,
            )
            session.add(enrollment)
            session.flush()
            session.add(
                EnrollmentFeeTerm(
                    enrollment_id=enrollment.enrollment_id,
                    agreed_amount=payload.agreed_fee_amount,
                    reason=payload.fee_reason,
                    created_by=created_by,
                )
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "student_conflict",
            "Student or initial enrollment conflicts with existing records",
        ) from None
    session.refresh(student)
    return student


def update_student(
    session: Session,
    student_id: int,
    payload: StudentUpdate,
    admin_id: int,
    request_id=None,
) -> Student:
    repository = StudentRepository(session)
    student = repository.get(student_id)
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")

    changes = payload.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None)
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).lower()

    _ensure_unique_email(
        repository,
        changes.get("email", student.email),
        exclude_id=student_id,
    )

    requested_status = changes.pop("status", student.status)
    for field_name, value in changes.items():
        setattr(student, field_name, value)
    previous_status = student.status
    if requested_status == "archived" and student.status != "archived":
        student.status = "archived"
        student.archived_at = datetime.now(UTC)
    elif requested_status == "active":
        student.status = "active"
        student.archived_at = None
    student.updated_at = datetime.now(UTC)
    if previous_status != student.status:
        audit_lifecycle_action(
            session,
            admin_id=admin_id,
            action=f"student_{student.status}",
            target_type="student",
            target_id=student.student_id,
            reason=reason or f"Student status changed to {student.status}",
            request_id=request_id,
            metadata={"student_number": student.student_number, "status_before": previous_status},
        )
    return _commit_student(session, student)


def student_dependencies(session: Session, student_id: int) -> DependencySummary:
    student = get_student(session, student_id)
    enrollment_count = session.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.student_id == student_id)
    ) or 0
    return DependencySummary(
        resource="student",
        identifier=student.student_number,
        dependencies={"enrollments": enrollment_count},
        can_delete=enrollment_count == 0,
    )


def delete_student(
    session: Session, student_id: int, reason: str, admin_id: int, request_id=None
) -> None:
    student = StudentRepository(session).get(student_id, lock=True)
    if student is None:
        raise APIError(404, "student_not_found", "Student was not found")
    dependencies = student_dependencies(session, student_id)
    if not dependencies.can_delete:
        raise APIError(
            409,
            "student_has_history",
            (
                "Student cannot be permanently deleted: "
                f"{dependencies.dependencies['enrollments']} enrollment(s) reference this "
                "record. Archive it instead."
            ),
        )
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="student_deleted",
            target_type="student",
            target_id=student_id,
            request_id=request_id,
            metadata_={"student_number": student.student_number, "reason": reason},
        )
    )
    session.delete(student)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "student_delete_conflict",
            (
                "Student is referenced by historical records and cannot be deleted. "
                "Archive it instead."
            ),
        ) from None


def _ensure_unique_email(
    repository: StudentRepository,
    email: str | None,
    *,
    exclude_id: int | None = None,
) -> None:
    if email and repository.find_by_email(email, exclude_id=exclude_id) is not None:
        raise APIError(409, "duplicate_student_email", "A student with this email already exists")


def _commit_student(session: Session, student: Student) -> Student:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "student_conflict",
            "Student data conflicts with an existing record",
        ) from None
    session.refresh(student)
    return student