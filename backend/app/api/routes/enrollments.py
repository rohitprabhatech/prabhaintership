from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentPage,
    EnrollmentResponse,
    EnrollmentStatusUpdate,
)
from app.services.enrollment_service import (
    create_enrollment,
    get_enrollment,
    list_enrollments,
    update_enrollment_status,
)

router = APIRouter(
    prefix="/enrollments",
    tags=["enrollments"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment_endpoint(
    payload: EnrollmentCreate,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> EnrollmentResponse:
    enrollment = create_enrollment(session, payload, admin.admin_id)
    response.headers["Location"] = f"/api/v1/enrollments/{enrollment.enrollment_id}"
    return EnrollmentResponse.model_validate(enrollment)


@router.get("", response_model=EnrollmentPage)
def list_enrollments_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    student_id: Annotated[int | None, Query(gt=0)] = None,
    program_id: Annotated[int | None, Query(gt=0)] = None,
    batch_id: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[
        Literal["active", "completed", "withdrawn", "cancelled", "all"],
        Query(alias="status"),
    ] = "all",
    session: Session = Depends(get_db),
) -> EnrollmentPage:
    return list_enrollments(
        session,
        page=page,
        page_size=page_size,
        student_id=student_id,
        program_id=program_id,
        batch_id=batch_id,
        status=None if status_filter == "all" else status_filter,
        search=q,
    )


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> EnrollmentResponse:
    return EnrollmentResponse.model_validate(get_enrollment(session, enrollment_id))


@router.patch("/{enrollment_id}/status", response_model=EnrollmentResponse)
def update_enrollment_status_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    payload: EnrollmentStatusUpdate,
    session: Session = Depends(get_db),
) -> EnrollmentResponse:
    enrollment = update_enrollment_status(session, enrollment_id, payload.status)
    return EnrollmentResponse.model_validate(enrollment)
