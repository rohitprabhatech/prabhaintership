from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.program import ProgramCreate, ProgramPage, ProgramResponse, ProgramUpdate
from app.services.program_service import create_program, get_program, list_programs, update_program

router = APIRouter(
    prefix="/programs",
    tags=["internship-programs"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
def create_program_endpoint(
    payload: ProgramCreate,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> ProgramResponse:
    program = create_program(session, payload, admin.admin_id)
    response.headers["Location"] = f"/api/v1/programs/{program.program_id}"
    return ProgramResponse.model_validate(program)


@router.get("", response_model=ProgramPage)
def list_programs_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[
        Literal["draft", "active", "inactive", "all"], Query(alias="status")
    ] = "all",
    session: Session = Depends(get_db),
) -> ProgramPage:
    return list_programs(
        session,
        page=page,
        page_size=page_size,
        search=q,
        status=None if status_filter == "all" else status_filter,
    )


@router.get("/{program_id}", response_model=ProgramResponse)
def get_program_endpoint(
    program_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> ProgramResponse:
    return ProgramResponse.model_validate(get_program(session, program_id))


@router.patch("/{program_id}", response_model=ProgramResponse)
def update_program_endpoint(
    program_id: Annotated[int, Path(gt=0)],
    payload: ProgramUpdate,
    session: Session = Depends(get_db),
) -> ProgramResponse:
    return ProgramResponse.model_validate(update_program(session, program_id, payload))
