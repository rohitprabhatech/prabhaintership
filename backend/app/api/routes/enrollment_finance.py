from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.finance import (
    FeeAdjustmentCreate,
    FeeAdjustmentResponse,
    FeeSummary,
    FeeTermCreate,
    FeeTermResponse,
    PaymentAdjustmentCreate,
    PaymentAdjustmentResponse,
    PaymentCreate,
    PaymentPage,
    PaymentResponse,
)
from app.services.finance_service import (
    create_fee_adjustment,
    create_payment_adjustment,
    get_fee_summary,
    list_fee_adjustments,
    list_fee_terms,
    list_payment_adjustments,
    list_payments,
    post_payment,
    revise_fee_term,
)

router = APIRouter(
    prefix="/enrollments",
    tags=["enrollment-finance"],
    dependencies=[Depends(get_current_admin)],
)


def _request_id(request: Request) -> UUID | None:
    try:
        return UUID(request.state.request_id)
    except (AttributeError, ValueError):
        return None


@router.get("/{enrollment_id}/fees", response_model=FeeSummary)
def fee_summary_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> FeeSummary:
    return get_fee_summary(session, enrollment_id)


@router.get("/{enrollment_id}/fee-terms", response_model=list[FeeTermResponse])
def fee_terms_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> list[FeeTermResponse]:
    return list_fee_terms(session, enrollment_id)


@router.post(
    "/{enrollment_id}/fee-terms",
    response_model=FeeTermResponse,
    status_code=status.HTTP_201_CREATED,
)
def revise_fee_term_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    payload: FeeTermCreate,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> FeeTermResponse:
    term = revise_fee_term(session, enrollment_id, payload, admin.admin_id, _request_id(request))
    response.headers["Location"] = f"/api/v1/enrollments/{enrollment_id}/fee-terms"
    return term


@router.get("/{enrollment_id}/fee-adjustments", response_model=list[FeeAdjustmentResponse])
def fee_adjustments_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    session: Session = Depends(get_db),
) -> list[FeeAdjustmentResponse]:
    return list_fee_adjustments(session, enrollment_id)


@router.post(
    "/{enrollment_id}/fee-adjustments",
    response_model=FeeAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def approve_fee_adjustment_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    payload: FeeAdjustmentCreate,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> FeeAdjustmentResponse:
    adjustment, replayed = create_fee_adjustment(
        session,
        enrollment_id,
        payload,
        idempotency_key,
        admin.admin_id,
        _request_id(request),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
    return adjustment


@router.get("/{enrollment_id}/payments", response_model=PaymentPage)
def payment_history_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_db),
) -> PaymentPage:
    return list_payments(session, enrollment_id, page=page, page_size=page_size)


@router.post(
    "/{enrollment_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_payment_endpoint(
    enrollment_id: Annotated[int, Path(gt=0)],
    payload: PaymentCreate,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> PaymentResponse:
    payment, replayed = post_payment(
        session,
        enrollment_id,
        payload,
        idempotency_key,
        admin.admin_id,
        _request_id(request),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
    else:
        response.headers["Location"] = f"/api/v1/payments/{payment.payment_id}"
    return payment


payment_adjustment_router = APIRouter(
    prefix="/payments",
    tags=["payment-adjustments"],
    dependencies=[Depends(get_current_admin)],
)


@payment_adjustment_router.get(
    "/{payment_id}/adjustments", response_model=list[PaymentAdjustmentResponse]
)
def payment_adjustments_endpoint(
    payment_id: Annotated[int, Path(gt=0)], session: Session = Depends(get_db)
) -> list[PaymentAdjustmentResponse]:
    return list_payment_adjustments(session, payment_id)


@payment_adjustment_router.post(
    "/{payment_id}/adjustments",
    response_model=PaymentAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_payment_adjustment_endpoint(
    payment_id: Annotated[int, Path(gt=0)],
    payload: PaymentAdjustmentCreate,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
) -> PaymentAdjustmentResponse:
    adjustment, replayed = create_payment_adjustment(
        session,
        payment_id,
        payload,
        idempotency_key,
        admin.admin_id,
        _request_id(request),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
    return adjustment
