from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.batch import BatchCreate, BatchPage, BatchResponse, BatchUpdate
from app.schemas.enrollment import BatchRoster, BatchRosterStudent
from app.services.batch_service import (
    create_batch,
    get_batch,
    get_batch_roster,
    list_batches,
    update_batch,
)

router = APIRouter(
    prefix="/batches",
    tags=["batches"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch_endpoint(
    payload: BatchCreate,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> BatchResponse:
    batch = create_batch(session, payload, admin.admin_id)
    response.headers["Location"] = f"/api/v1/batches/{batch.batch_id}"
    return BatchResponse.model_validate(batch)


@router.get("", response_model=BatchPage)
def list_batches_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    program_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[
        Literal["planned", "active", "completed", "cancelled", "all"], Query(alias="status")
    ] = "all",
    session: Session = Depends(get_db),
) -> BatchPage:
    return list_batches(
        session,
        page=page,
        page_size=page_size,
        program_id=program_id,
        status=None if status_filter == "all" else status_filter,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch_endpoint(
    batch_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> BatchResponse:
    return BatchResponse.model_validate(get_batch(session, batch_id))


@router.patch("/{batch_id}", response_model=BatchResponse)
def update_batch_endpoint(
    batch_id: Annotated[int, Path(gt=0)],
    payload: BatchUpdate,
    session: Session = Depends(get_db),
) -> BatchResponse:
    return BatchResponse.model_validate(update_batch(session, batch_id, payload))


@router.get("/{batch_id}/roster", response_model=BatchRoster)
def batch_roster_endpoint(
    batch_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> BatchRoster:
    batch, rows, active_count = get_batch_roster(session, batch_id)
    students = [
        BatchRosterStudent(
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
        )
        for enrollment, student in rows
    ]
    return BatchRoster(
        batch_id=batch.batch_id,
        program_id=batch.program_id,
        batch_code=batch.batch_code,
        name=batch.name,
        starts_on=batch.starts_on,
        ends_on=batch.ends_on,
        capacity=batch.capacity,
        active_enrollment_count=active_count,
        students=students,
    )
