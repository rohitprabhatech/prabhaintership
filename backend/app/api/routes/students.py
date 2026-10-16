from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.student import StudentCreate, StudentPage, StudentResponse, StudentUpdate
from app.services.student_service import (
    create_student,
    get_student,
    list_students,
    update_student,
)

router = APIRouter(
    prefix="/students",
    tags=["students"],
    dependencies=[Depends(get_current_admin)],
)


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
    session: Session = Depends(get_db),
) -> StudentPage:
    status_value = None if status_filter == "all" else status_filter
    return list_students(
        session,
        page=page,
        page_size=page_size,
        search=q,
        status=status_value,
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> StudentResponse:
    return StudentResponse.model_validate(get_student(session, student_id))


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_endpoint(
    student_id: Annotated[int, Path(gt=0)],
    payload: StudentUpdate,
    session: Session = Depends(get_db),
) -> StudentResponse:
    return StudentResponse.model_validate(update_student(session, student_id, payload))