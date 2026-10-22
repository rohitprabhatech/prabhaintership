from datetime import UTC, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.errors import APIError
from app.models.audit_log import AuditLog
from app.models.enrollment_fee_term import EnrollmentFeeTerm
from app.models.fee_adjustment import FeeAdjustment
from app.models.payment import Payment
from app.models.payment_adjustment import PaymentAdjustment
from app.repositories.finance_repository import FinanceRepository
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


def get_fee_summary(session: Session, enrollment_id: int) -> FeeSummary:
    repository = FinanceRepository(session)
    if repository.get_enrollment(enrollment_id) is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    balance = repository.get_balance(enrollment_id)
    if balance is None:
        raise APIError(409, "enrollment_fee_missing", "Enrollment has no current fee term")
    return FeeSummary(
        enrollment_id=balance["enrollment_id"],
        enrollment_number=balance["enrollment_number"],
        fee_term_id=balance["fee_term_id"],
        base_fee=balance["fee_amount"],
        adjustments_total=balance["adjustments_total"],
        effective_fee=balance["effective_fee"],
        currency=balance["currency"].strip(),
        net_paid=balance["net_paid"],
        pending_balance=balance["pending_balance"],
    )


def list_fee_terms(session: Session, enrollment_id: int) -> list[FeeTermResponse]:
    repository = FinanceRepository(session)
    if repository.get_enrollment(enrollment_id) is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    return [
        FeeTermResponse.model_validate(term) for term in repository.list_fee_terms(enrollment_id)
    ]


def revise_fee_term(
    session: Session,
    enrollment_id: int,
    payload: FeeTermCreate,
    admin_id: int,
    request_id: UUID | None,
) -> FeeTermResponse:
    repository = FinanceRepository(session)
    enrollment = repository.get_enrollment(enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    current = repository.get_current_fee_term(enrollment_id, lock=True)
    if current is None:
        raise APIError(409, "enrollment_fee_missing", "Enrollment has no current fee term")
    balance = repository.get_balance(enrollment_id)
    if (
        balance is None
        or payload.agreed_amount + balance["adjustments_total"] < balance["net_paid"]
    ):
        raise APIError(
            409, "fee_below_net_paid", "New fee cannot be less than net payments received"
        )

    now = datetime.now(UTC)
    current.effective_to = now
    term = EnrollmentFeeTerm(
        enrollment_id=enrollment_id,
        agreed_amount=payload.agreed_amount,
        currency="INR",
        effective_from=now,
        reason=payload.reason,
        created_by=admin_id,
    )
    session.add(term)
    try:
        session.flush()
        _add_audit(
            session,
            admin_id,
            "enrollment_fee_revised",
            "enrollment_fee_term",
            term.fee_term_id,
            request_id,
            {
                "enrollment_id": enrollment_id,
                "amount": str(payload.agreed_amount),
                "reason": payload.reason,
            },
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise APIError(
            409, "fee_revision_conflict", "Fee revision conflicts with the ledger"
        ) from None
    except DBAPIError:
        session.rollback()
        raise
    session.refresh(term)
    return FeeTermResponse.model_validate(term)


def create_fee_adjustment(
    session: Session,
    enrollment_id: int,
    payload: FeeAdjustmentCreate,
    idempotency_key: UUID,
    admin_id: int,
    request_id: UUID | None,
) -> tuple[FeeAdjustmentResponse, bool]:
    repository = FinanceRepository(session)
    enrollment = repository.get_enrollment(enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")

    previous = repository.get_fee_adjustment_by_key(idempotency_key)
    if previous is not None:
        if (
            previous.enrollment_id != enrollment_id
            or previous.adjustment_type != payload.adjustment_type
            or previous.amount != payload.amount
            or previous.reason != payload.reason
        ):
            raise APIError(
                409, "idempotency_key_reused", "Idempotency key was used with different data"
            )
        return FeeAdjustmentResponse.model_validate(previous), True

    balance = repository.get_balance(enrollment_id)
    if balance is None:
        raise APIError(409, "enrollment_fee_missing", "Enrollment has no current fee term")
    adjustment_effect = (
        payload.amount if payload.adjustment_type == "fee_increase" else -payload.amount
    )
    new_effective_fee = balance["effective_fee"] + adjustment_effect
    if new_effective_fee < 0 or new_effective_fee < balance["net_paid"]:
        raise APIError(
            409,
            "fee_adjustment_below_net_paid",
            "Approved adjustment cannot reduce the fee below net payments received",
        )

    adjustment = FeeAdjustment(
        enrollment_id=enrollment_id,
        adjustment_type=payload.adjustment_type,
        amount=payload.amount,
        reason=payload.reason,
        approved_by=admin_id,
        idempotency_key=idempotency_key,
    )
    session.add(adjustment)
    try:
        session.flush()
        _add_audit(
            session,
            admin_id,
            f"fee_{payload.adjustment_type}_approved",
            "fee_adjustment",
            adjustment.fee_adjustment_id,
            request_id,
            {
                "enrollment_id": enrollment_id,
                "amount": str(payload.amount),
                "reason": payload.reason,
            },
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = repository.get_fee_adjustment_by_key(idempotency_key)
        if previous is not None and _same_fee_adjustment(previous, enrollment_id, payload):
            return FeeAdjustmentResponse.model_validate(previous), True
        raise APIError(
            409, "fee_adjustment_conflict", "Fee adjustment conflicts with the ledger"
        ) from None
    except DBAPIError:
        session.rollback()
        raise
    session.refresh(adjustment)
    return FeeAdjustmentResponse.model_validate(adjustment), False


def list_fee_adjustments(session: Session, enrollment_id: int) -> list[FeeAdjustmentResponse]:
    repository = FinanceRepository(session)
    if repository.get_enrollment(enrollment_id) is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    return [
        FeeAdjustmentResponse.model_validate(adjustment)
        for adjustment in repository.list_fee_adjustments(enrollment_id)
    ]


def post_payment(
    session: Session,
    enrollment_id: int,
    payload: PaymentCreate,
    idempotency_key: UUID,
    admin_id: int,
    request_id: UUID | None,
) -> tuple[PaymentResponse, bool]:
    repository = FinanceRepository(session)
    enrollment = repository.get_enrollment(enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")

    previous = repository.get_payment_by_key(idempotency_key)
    if previous is not None:
        if not _same_payment(previous, enrollment_id, payload):
            raise APIError(
                409, "idempotency_key_reused", "Idempotency key was used with different data"
            )
        status_row = repository.get_payment_status(previous.payment_id)
        return PaymentResponse.model_validate(status_row), True

    balance = repository.get_balance(enrollment_id)
    if balance is None:
        raise APIError(409, "enrollment_fee_missing", "Enrollment has no current fee term")
    if payload.amount > balance["pending_balance"]:
        raise APIError(
            409, "overpayment_rejected", "Payment exceeds the pending enrollment balance"
        )

    paid_at = payload.paid_at or datetime.now(UTC)
    if paid_at.tzinfo is None or paid_at.utcoffset() is None:
        raise APIError(422, "timezone_required", "Payment date must include a timezone")
    payment = Payment(
        enrollment_id=enrollment_id,
        idempotency_key=idempotency_key,
        amount=payload.amount,
        currency="INR",
        paid_at=paid_at,
        payment_method=payload.payment_method,
        payment_reference=payload.payment_reference,
        recorded_by=admin_id,
    )
    session.add(payment)
    try:
        session.flush()
        _add_audit(
            session,
            admin_id,
            "payment_recorded",
            "payment",
            payment.payment_id,
            request_id,
            {
                "enrollment_id": enrollment_id,
                "amount": str(payload.amount),
                "payment_method": payload.payment_method,
            },
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = repository.get_payment_by_key(idempotency_key)
        if previous is not None and _same_payment(previous, enrollment_id, payload):
            status_row = repository.get_payment_status(previous.payment_id)
            return PaymentResponse.model_validate(status_row), True
        raise APIError(
            409,
            "payment_conflict",
            "Payment reference or idempotency key conflicts with an existing receipt",
        ) from None
    except DBAPIError:
        session.rollback()
        raise
    status_row = repository.get_payment_status(payment.payment_id)
    return PaymentResponse.model_validate(status_row), False


def list_payments(
    session: Session, enrollment_id: int, *, page: int, page_size: int
) -> PaymentPage:
    repository = FinanceRepository(session)
    if repository.get_enrollment(enrollment_id) is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")
    rows, total = repository.list_payments(enrollment_id, page=page, page_size=page_size)
    return PaymentPage(
        items=[PaymentResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def create_payment_adjustment(
    session: Session,
    payment_id: int,
    payload: PaymentAdjustmentCreate,
    idempotency_key: UUID,
    admin_id: int,
    request_id: UUID | None,
) -> tuple[PaymentAdjustmentResponse, bool]:
    repository = FinanceRepository(session)
    payment = repository.get_payment(payment_id)
    if payment is None:
        raise APIError(404, "payment_not_found", "Payment was not found")
    enrollment = repository.get_enrollment(payment.enrollment_id, lock=True)
    if enrollment is None:
        raise APIError(404, "enrollment_not_found", "Enrollment was not found")

    previous = repository.get_payment_adjustment_by_key(idempotency_key)
    if previous is not None:
        if (
            previous.payment_id != payment_id
            or previous.adjustment_type != payload.adjustment_type
            or previous.amount != payload.amount
            or previous.reason != payload.reason
        ):
            raise APIError(
                409, "idempotency_key_reused", "Idempotency key was used with different data"
            )
        return PaymentAdjustmentResponse.model_validate(previous), True

    payment = repository.get_payment(payment_id)
    if payment is None:
        raise APIError(404, "payment_not_found", "Payment was not found")
    adjusted = repository.adjusted_amount_for_payment(payment_id) or Decimal("0.00")
    remaining = payment.amount - adjusted
    if payload.amount > remaining:
        raise APIError(
            409, "adjustment_exceeds_payment", "Refund exceeds the remaining receipt amount"
        )
    if payload.adjustment_type == "reversal" and payload.amount != remaining:
        raise APIError(
            422, "reversal_must_be_full", "A reversal must reverse the full remaining receipt"
        )

    adjustment = PaymentAdjustment(
        payment_id=payment_id,
        idempotency_key=idempotency_key,
        adjustment_type=payload.adjustment_type,
        amount=payload.amount,
        reason=payload.reason,
        recorded_by=admin_id,
    )
    session.add(adjustment)
    try:
        session.flush()
        _add_audit(
            session,
            admin_id,
            f"payment_{payload.adjustment_type}",
            "payment_adjustment",
            adjustment.adjustment_id,
            request_id,
            {"payment_id": payment_id, "amount": str(payload.amount), "reason": payload.reason},
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        previous = repository.get_payment_adjustment_by_key(idempotency_key)
        if previous is not None and _same_payment_adjustment(previous, payment_id, payload):
            return PaymentAdjustmentResponse.model_validate(previous), True
        raise APIError(
            409, "payment_adjustment_conflict", "Payment adjustment conflicts with the ledger"
        ) from None
    except DBAPIError:
        session.rollback()
        raise
    session.refresh(adjustment)
    return PaymentAdjustmentResponse.model_validate(adjustment), False


def list_payment_adjustments(session: Session, payment_id: int) -> list[PaymentAdjustmentResponse]:
    repository = FinanceRepository(session)
    if repository.get_payment(payment_id) is None:
        raise APIError(404, "payment_not_found", "Payment was not found")
    return [
        PaymentAdjustmentResponse.model_validate(adjustment)
        for adjustment in repository.list_payment_adjustments(payment_id)
    ]


def _add_audit(
    session: Session,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: int,
    request_id: UUID | None,
    metadata: dict,
) -> None:
    session.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            metadata_=metadata,
        )
    )


def _same_payment(existing: Payment, enrollment_id: int, payload: PaymentCreate) -> bool:
    return (
        existing.enrollment_id == enrollment_id
        and existing.amount == payload.amount
        and existing.payment_method == payload.payment_method
        and existing.payment_reference == payload.payment_reference
        and (payload.paid_at is None or existing.paid_at == payload.paid_at)
    )


def _same_fee_adjustment(
    existing: FeeAdjustment, enrollment_id: int, payload: FeeAdjustmentCreate
) -> bool:
    return (
        existing.enrollment_id == enrollment_id
        and existing.adjustment_type == payload.adjustment_type
        and existing.amount == payload.amount
        and existing.reason == payload.reason
    )


def _same_payment_adjustment(
    existing: PaymentAdjustment, payment_id: int, payload: PaymentAdjustmentCreate
) -> bool:
    return (
        existing.payment_id == payment_id
        and existing.adjustment_type == payload.adjustment_type
        and existing.amount == payload.amount
        and existing.reason == payload.reason
    )
