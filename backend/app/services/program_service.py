from math import ceil

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.internship_program import InternshipProgram
from app.repositories.program_repository import ProgramRepository
from app.schemas.program import ProgramCreate, ProgramPage, ProgramUpdate

_PROGRAM_TRANSITIONS = {
    "draft": {"active", "inactive"},
    "active": {"inactive"},
    "inactive": {"active"},
}


def create_program(session: Session, payload: ProgramCreate, admin_id: int) -> InternshipProgram:
    repository = ProgramRepository(session)
    if repository.find_by_code(payload.program_code):
        raise APIError(409, "duplicate_program_code", "A program with this code already exists")
    program = InternshipProgram(**payload.model_dump(), created_by=admin_id)
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


def update_program(session: Session, program_id: int, payload: ProgramUpdate) -> InternshipProgram:
    repository = ProgramRepository(session)
    program = repository.get(program_id, lock=True)
    if program is None:
        raise APIError(404, "program_not_found", "Internship program was not found")
    changes = payload.model_dump(exclude_unset=True)
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
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "program_conflict", "Program conflicts with an existing record"
        ) from None
    session.refresh(program)
    return program


def _commit(session: Session, program: InternshipProgram, code: str) -> InternshipProgram:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(409, code, "Program conflicts with an existing record") from None
    session.refresh(program)
    return program
