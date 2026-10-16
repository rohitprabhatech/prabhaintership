from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.finance import (
    CertificateEventCreate,
    CertificateEventResponse,
    CertificateIssueCreate,
    CertificateReplacementCreate,
    CertificateReportPage,
    CertificateResponse,
)
from app.services.certificate_service import (
    get_certificate,
    issue_certificate,
    list_certificate_events,
    list_certificates,
    record_certificate_correction,
    replace_certificate,
    revoke_certificate,
)

router = APIRouter(
    prefix="/certificates", tags=["certificates"], dependencies=[Depends(get_current_admin)]
)


def _request_id(request: Request) -> UUID | None:
    try:
        return UUID(request.state.request_id)
    except (AttributeError, ValueError):
        return None


@router.post("", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
def issue_certificate_endpoint(
    payload: CertificateIssueCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> CertificateResponse:
    certificate = issue_certificate(session, payload, admin.admin_id, _request_id(request))
    return certificate


@router.get("", response_model=CertificateReportPage)
def certificate_report_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[
        Literal["issued", "replaced", "revoked", "all"], Query(alias="status")
    ] = "all",
    enrollment_id: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(max_length=128)] = None,
    session: Session = Depends(get_db),
) -> CertificateReportPage:
    return list_certificates(
        session,
        page=page,
        page_size=page_size,
        status=None if status_filter == "all" else status_filter,
        enrollment_id=enrollment_id,
        search=q,
    )


@router.get("/{certificate_id}", response_model=CertificateResponse)
def get_certificate_endpoint(
    certificate_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> CertificateResponse:
    return get_certificate(session, certificate_id)


@router.get("/{certificate_id}/events", response_model=list[CertificateEventResponse])
def certificate_events_endpoint(
    certificate_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> list[CertificateEventResponse]:
    return list_certificate_events(session, certificate_id)


@router.post(
    "/{certificate_id}/replacement",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
def replace_certificate_endpoint(
    certificate_id: Annotated[int, Path(gt=0)],
    payload: CertificateReplacementCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> CertificateResponse:
    return replace_certificate(
        session, certificate_id, payload, admin.admin_id, _request_id(request)
    )


@router.post(
    "/{certificate_id}/revocation",
    response_model=CertificateEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def revoke_certificate_endpoint(
    certificate_id: Annotated[int, Path(gt=0)],
    payload: CertificateEventCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> CertificateEventResponse:
    return revoke_certificate(
        session, certificate_id, payload, admin.admin_id, _request_id(request)
    )


@router.post(
    "/{certificate_id}/corrections",
    response_model=CertificateEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def certificate_correction_endpoint(
    certificate_id: Annotated[int, Path(gt=0)],
    payload: CertificateEventCreate,
    request: Request,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> CertificateEventResponse:
    return record_certificate_correction(
        session, certificate_id, payload, admin.admin_id, _request_id(request)
    )
