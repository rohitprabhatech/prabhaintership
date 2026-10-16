from datetime import UTC, datetime
from math import ceil

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.enrollment import Enrollment
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.repositories.project_repository import ProjectRepository
from app.schemas.finance import (
    ProjectAssignmentCreate,
    ProjectAssignmentResponse,
    ProjectAssignmentStatusUpdate,
    ProjectCreate,
    ProjectResponse,
)

_PROJECT_ASSIGNMENT_TRANSITIONS = {
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def create_project(
    session: Session, payload: ProjectCreate, admin_id: int, request_id
) -> ProjectResponse:
    repository = ProjectRepository(session)
    if repository.find_project_code(payload.project_code):
        raise APIError(409, "duplicate_project_code", "Project code already exists")
    project = Project(**payload.model_dump(), created_by=admin_id)
    session.add(project)
    try:
        session.flush()
        _audit(session, admin_id, "project_created", "project", project.project_id, request_id)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "project_conflict", "Project conflicts with an existing record"
        ) from None
    session.refresh(project)
    return ProjectResponse.model_validate(project)


def list_projects(session: Session, *, page: int, page_size: int, status: str | None):
    rows, total = ProjectRepository(session).list_projects(
        page=page, page_size=page_size, status=status
    )
    return {
        "items": [ProjectResponse.model_validate(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }


def get_project(session: Session, project_id: int) -> ProjectResponse:
    project = ProjectRepository(session).get_project(project_id)
    if project is None:
        raise APIError(404, "project_not_found", "Project was not found")
    return ProjectResponse.model_validate(project)


def create_assignment(
    session: Session,
    enrollment_id: int,
    payload: ProjectAssignmentCreate,
    admin_id: int,
    request_id,
) -> ProjectAssignmentResponse:
    repository = ProjectRepository(session)
    enrollment = session.scalar(
        select(Enrollment).where(Enrollment.enrollment_id == enrollment_id).with_for_update()
    )
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    if enrollment.status != "active":
        raise APIError(
            409, "enrollment_not_active", "Project assignment requires an active enrollment"
        )
    project = repository.get_project(payload.project_id)
    if project is None:
        raise APIError(404, "project_not_found", "Project was not found")
    if project.status != "active":
        raise APIError(409, "project_not_active", "Archived projects cannot receive assignments")
    if repository.find_assignment(project.project_id, enrollment_id):
        raise APIError(
            409, "duplicate_project_assignment", "Project is already assigned to this enrollment"
        )

    assignment = ProjectAssignment(
        project_id=project.project_id,
        enrollment_id=enrollment_id,
        assigned_by=admin_id,
    )
    session.add(assignment)
    try:
        session.flush()
        _audit(
            session,
            admin_id,
            "project_assigned",
            "project_assignment",
            assignment.project_assignment_id,
            request_id,
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "project_assignment_conflict", "Project assignment already exists"
        ) from None
    session.refresh(assignment)
    return ProjectAssignmentResponse(
        **{
            **ProjectAssignmentResponse.model_validate(assignment).model_dump(),
            "project_code": project.project_code,
            "project_name": project.name,
        }
    )


def list_assignments(
    session: Session,
    *,
    page: int,
    page_size: int,
    enrollment_id: int | None,
    project_id: int | None,
    status: str | None,
):
    rows, total = ProjectRepository(session).list_assignments(
        page=page,
        page_size=page_size,
        enrollment_id=enrollment_id,
        project_id=project_id,
        status=status,
    )
    items = []
    for assignment, project in rows:
        base = ProjectAssignmentResponse.model_validate(assignment).model_dump()
        base.update(project_code=project.project_code, project_name=project.name)
        items.append(ProjectAssignmentResponse(**base))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }


def update_assignment_status(
    session: Session,
    assignment_id: int,
    payload: ProjectAssignmentStatusUpdate,
    admin_id: int,
    request_id,
) -> ProjectAssignmentResponse:
    repository = ProjectRepository(session)
    assignment = repository.get_assignment(assignment_id, lock=True)
    if assignment is None:
        raise APIError(404, "project_assignment_not_found", "Project assignment was not found")
    requested = payload.status
    if requested == assignment.status:
        project = repository.get_project(assignment.project_id)
        response = ProjectAssignmentResponse.model_validate(assignment).model_dump()
        response.update(project_code=project.project_code, project_name=project.name)
        return ProjectAssignmentResponse(**response)
    if requested not in _PROJECT_ASSIGNMENT_TRANSITIONS[assignment.status]:
        raise APIError(
            409,
            "invalid_project_status_transition",
            "Project assignment status transition is not allowed",
        )

    assignment.status = requested
    assignment.completed_at = datetime.now(UTC) if requested == "completed" else None
    assignment.updated_at = datetime.now(UTC)
    project = repository.get_project(assignment.project_id)
    try:
        session.flush()
        _audit(
            session,
            admin_id,
            f"project_assignment_{requested}",
            "project_assignment",
            assignment_id,
            request_id,
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "project_assignment_conflict", "Project assignment update conflicts"
        ) from None
    session.refresh(assignment)
    response = ProjectAssignmentResponse.model_validate(assignment).model_dump()
    response.update(project_code=project.project_code, project_name=project.name)
    return ProjectAssignmentResponse(**response)


def _audit(
    session: Session, admin_id: int, action: str, target_type: str, target_id: int, request_id
) -> None:
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            metadata_={},
        )
    )
