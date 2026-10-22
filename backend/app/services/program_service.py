from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.batch import Batch
from app.models.enrollment import Enrollment
from app.models.fee_structure import FeeStructure
from app.models.internship_program import InternshipProgram
from app.repositories.program_repository import ProgramRepository
from app.schemas.lifecycle import DependencySummary
from app.schemas.program import ProgramCreate, ProgramPage, ProgramUpdate
from app.services.business_number_service import generate_business_number
from app.services.lifecycle import audit_lifecycle_action

_PROGRAM_TRANSITIONS = {
    "draft": {"active", "inactive"},
    "active": {"inactive"},
    "inactive": {"active"},
}


def create_program(session: Session, payload: ProgramCreate, admin_id: int) -> InternshipProgram:
    program = InternshipProgram(
        **payload.model_dump(),
        program_code=generate_business_number(session, "program"),
        created_by=admin_id,
    )
    session.add(program)
    return _commit(session, program, "program_conflict")


def list_programs(
    session: Session, *, page: int, page_size: int, search: str | None, status: str | None
) -> ProgramPage:
    rows, total = ProgramRepository(session).list(
        page=page, page_size=page_size, search=search.strip() if search else None, status=status
    )
    return ProgramPage(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_program(session: Session, program_id: int) -> InternshipProgram:
    program = ProgramRepository(session).get(program_id)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    return program


def update_program(
    session: Session,
    program_id: int,
    payload: ProgramUpdate,
    admin_id: int,
    request_id=None,
) -> InternshipProgram:
    repository = ProgramRepository(session)
    program = repository.get(program_id, lock=True)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    changes = payload.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None)
    previous_status = program.status
    requested_status = changes.pop("status", program.status)
    if (
        requested_status != program.status
        and requested_status not in _PROGRAM_TRANSITIONS[program.status]
    ):
        raise APIError(
            409, "invalid_program_status_transition", "Program status transition is not allowed"
        )
    for field_name, value in changes.items():
        setattr(program, field_name, value)
    program.status = requested_status
    if requested_status != previous_status:
        audit_lifecycle_action(
            session,
            admin_id=admin_id,
            action=f"program_{requested_status}",
            target_type="internship_program",
            target_id=program_id,
            reason=reason or f"Program status changed to {requested_status}",
            request_id=request_id,
            metadata={"program_code": program.program_code, "status_before": previous_status},
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "program_conflict", "Program conflicts with an existing record"
        ) from None
    session.refresh(program)
    return program


def program_dependencies(session: Session, program_id: int) -> DependencySummary:
    program = get_program(session, program_id)
    batches = session.scalar(
        select(func.count()).select_from(Batch).where(Batch.program_id == program_id)
    ) or 0
    enrollments = session.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.program_id == program_id)
    ) or 0
    fee_structures = session.scalar(
        select(func.count())
        .select_from(FeeStructure)
        .where(FeeStructure.program_id == program_id)
    ) or 0
    return DependencySummary(
        resource="program",
        identifier=program.program_code,
        dependencies={
            "batches": batches,
            "enrollments": enrollments,
            "fee_structures": fee_structures,
        },
        can_delete=batches == 0 and enrollments == 0 and fee_structures == 0,
    )


def delete_program(
    session: Session, program_id: int, reason: str, admin_id: int, request_id=None
) -> None:
    program = ProgramRepository(session).get(program_id, lock=True)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    dependencies = program_dependencies(session, program_id)
    if not dependencies.can_delete:
        raise APIError(
            409,
            "program_has_history",
            (
                "Program cannot be permanently deleted while batches or enrollments "
                "reference it. Deactivate it instead."
            ),
        )
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="program_deleted",
            target_type="internship_program",
            target_id=program_id,
            request_id=request_id,
            metadata_={"program_code": program.program_code, "reason": reason},
        )
    )
    session.delete(program)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409,
            "program_delete_conflict",
            (
                "Program is referenced by historical records and cannot be deleted. "
                "Deactivate it instead."
            ),
        ) from None


def _commit(session: Session, program: InternshipProgram, code: str) -> InternshipProgram:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(409, code, "Program conflicts with an existing record") from None
    session.refresh(program)
    return program
