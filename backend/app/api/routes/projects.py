from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.finance import (
    ProjectAssignmentCreate,
    ProjectAssignmentPage,
    ProjectAssignmentResponse,
    ProjectAssignmentStatusUpdate,
    ProjectCreate,
    ProjectDelete,
    ProjectPage,
    ProjectResponse,
    ProjectStatusUpdate,
)
from app.schemas.lifecycle import DependencySummary
from app.services.project_service import (
    create_assignment,
    create_project,
    delete_project,
    get_project,
    list_assignments,
    list_projects,
    project_dependencies,
    update_assignment_status,
    update_project_status,
)

router = APIRouter(tags=["projects"], dependencies=[Depends(get_current_admin)])


def _request_id(request: Request) -> UUID | None:
    try:
        return UUID(request.state.request_id)
    except (AttributeError, ValueError):
        return None


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> ProjectResponse:
    return create_project(session, payload, admin.admin_id, _request_id(request))


@router.get("/projects", response_model=ProjectPage)
def list_projects_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[Literal["active", "archived", "all"], Query(alias="status")] = "all",
    session: Session = Depends(get_db),
) -> ProjectPage:
    return list_projects(
        session,
        page=page,
        page_size=page_size,
        status=None if status_filter == "all" else status_filter,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(
    project_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> ProjectResponse:
    return get_project(session, project_id)


@router.patch("/projects/{project_id}/status", response_model=ProjectResponse)
def update_project_status_endpoint(
    project_id: Annotated[int, Path(gt=0)],
    payload: ProjectStatusUpdate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> ProjectResponse:
    return update_project_status(
        session, project_id, payload, admin.admin_id, _request_id(request)
    )


@router.get("/projects/{project_id}/dependencies", response_model=DependencySummary)
def project_dependencies_endpoint(
    project_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> DependencySummary:
    return project_dependencies(session, project_id)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: Annotated[int, Path(gt=0)],
    payload: ProjectDelete,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> Response:
    delete_project(session, project_id, payload, admin.admin_id, _request_id(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/enrollments/{enrollment_id}/projects",
    response_model=ProjectAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_project_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    payload: ProjectAssignmentCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> ProjectAssignmentResponse:
    return create_assignment(session, enrollment_id, payload, admin.admin_id, _request_id(request))


@router.get("/project-assignments", response_model=ProjectAssignmentPage)
def list_assignments_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    enrollment_id: Annotated[int | None, Query(gt=0)] = None,
    project_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[
        Literal["assigned", "in_progress", "completed", "cancelled", "all"],
        Query(alias="status"),
    ] = "all",
    session: Session = Depends(get_db),
) -> ProjectAssignmentPage:
    return list_assignments(
        session,
        page=page,
        page_size=page_size,
        enrollment_id=enrollment_id,
        project_id=project_id,
        status=None if status_filter == "all" else status_filter,
    )


@router.patch(
    "/project-assignments/{assignment_id}/status",
    response_model=ProjectAssignmentResponse,
)
def update_assignment_status_endpoint(
    assignment_id: Annotated[int, Path(gt=0)],
    payload: ProjectAssignmentStatusUpdate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> ProjectAssignmentResponse:
    return update_assignment_status(
        session, assignment_id, payload, admin.admin_id, _request_id(request)
    )
