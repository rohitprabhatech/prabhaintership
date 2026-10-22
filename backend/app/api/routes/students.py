from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.lifecycle import DependencySummary
from app.schemas.student import (
    StudentActivityItem,
    StudentCreate,
    StudentDelete,
    StudentPage,
    StudentResponse,
    StudentUpdate,
)
from app.services.student_service import (
    create_student,
    delete_student,
    get_student,
    list_students,
    student_dependencies,
    student_activity,
    update_student,
)

router = APIRouter(
    prefix="/students",
    tags=["students"],
    dependencies=[Depends(get_current_admin)],
)


def _request_id(request: Request) -> UUID | None:
    try:
        return UUID(request.state.request_id)
    except (AttributeError, ValueError):
        return None


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(
    payload: StudentCreate,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> StudentResponse:
    student = create_student(session, payload, admin.admin_id)
    response.headers["Location"] = f"/api/v1/students/{student.student_id}"
    return StudentResponse.model_validate(student)


@router.get("", response_model=StudentPage)
def list_students_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[
        Literal["active", "archived", "all"], Query(alias="status")
    ] = "active",
    program_id: Annotated[int | None, Query(gt=0)] = None,
    batch_id: Annotated[int | None, Query(gt=0)] = None,
    enrollment_status: Annotated[
        Literal["active", "completed", "withdrawn", "cancelled"] | None, Query()
    ] = None,
    fee_status: Annotated[Literal["outstanding", "paid"] | None, Query()] = None,
    session: Session = Depends(get_db),
) -> StudentPage:
    status_value = None if status_filter == "all" else status_filter
    return list_students(
        session,
        page=page,
        page_size=page_size,
        search=q,
        status=status_value,
        program_id=program_id,
        batch_id=batch_id,
        enrollment_status=enrollment_status,
        fee_status=fee_status,
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> StudentResponse:
    return StudentResponse.model_validate(get_student(session, student_id))


@router.get("/{student_id}/activity", response_model=list[StudentActivityItem])
def student_activity_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> list[StudentActivityItem]:
    return student_activity(session, student_id)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    payload: StudentUpdate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> StudentResponse:
    return StudentResponse.model_validate(
        update_student(session, student_id, payload, admin.admin_id, _request_id(request))
    )


@router.get("/{student_id}/dependencies", response_model=DependencySummary)
def student_dependencies_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> DependencySummary:
    return student_dependencies(session, student_id)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    payload: StudentDelete,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> Response:
    delete_student(session, student_id, payload.reason, admin.admin_id, _request_id(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)