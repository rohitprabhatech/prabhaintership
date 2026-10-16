from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.enrollment_fee_term import EnrollmentFeeTerm
from app.models.fee_adjustment import FeeAdjustment
from app.models.payment import Payment
from app.models.payment_adjustment import PaymentAdjustment


class FinanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_enrollment(self, enrollment_id: int, *, lock: bool = False) -> Enrollment | None:
        statement = select(Enrollment).where(Enrollment.enrollment_id == enrollment_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_balance(self, enrollment_id: int) -> dict | None:
        row = (
            self.session.execute(
                text(
                    "SELECT enrollment_id, enrollment_number, fee_term_id, fee_amount, "
                    "adjustments_total, effective_fee, currency, net_paid, pending_balance "
                    "FROM internship_management.v_enrollment_balances "
                    "WHERE enrollment_id = :enrollment_id"
                ),
                {"enrollment_id": enrollment_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def get_current_fee_term(
        self, enrollment_id: int, *, lock: bool = False
    ) -> EnrollmentFeeTerm | None:
        statement = select(EnrollmentFeeTerm).where(
            EnrollmentFeeTerm.enrollment_id == enrollment_id,
            EnrollmentFeeTerm.effective_to.is_(None),
        )
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_fee_terms(self, enrollment_id: int) -> list[EnrollmentFeeTerm]:
        return list(
            self.session.scalars(
                select(EnrollmentFeeTerm)
                .where(EnrollmentFeeTerm.enrollment_id == enrollment_id)
                .order_by(
                    EnrollmentFeeTerm.effective_from.desc(), EnrollmentFeeTerm.fee_term_id.desc()
                )
            ).all()
        )

    def list_fee_adjustments(self, enrollment_id: int) -> list[FeeAdjustment]:
        return list(
            self.session.scalars(
                select(FeeAdjustment)
                .where(FeeAdjustment.enrollment_id == enrollment_id)
                .order_by(FeeAdjustment.approved_at.desc(), FeeAdjustment.fee_adjustment_id.desc())
            ).all()
        )

    def get_fee_adjustment_by_key(self, key):
        return self.session.scalar(
            select(FeeAdjustment).where(FeeAdjustment.idempotency_key == key)
        )

    def get_payment_by_key(self, key) -> Payment | None:
        return self.session.scalar(select(Payment).where(Payment.idempotency_key == key))

    def get_payment(self, payment_id: int, *, lock: bool = False) -> Payment | None:
        statement = select(Payment).where(Payment.payment_id == payment_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_payment_adjustment_by_key(self, key) -> PaymentAdjustment | None:
        return self.session.scalar(
            select(PaymentAdjustment).where(PaymentAdjustment.idempotency_key == key)
        )

    def list_payments(self, enrollment_id: int, *, page: int, page_size: int):
        count = self.session.execute(
            text(
                "SELECT count(*) FROM internship_management.v_payment_status "
                "WHERE enrollment_id = :enrollment_id"
            ),
            {"enrollment_id": enrollment_id},
        ).scalar_one()
        rows = (
            self.session.execute(
                text(
                    "SELECT payment_id, enrollment_id, amount, currency, paid_at, payment_method, "
                    "payment_reference, recorded_by, created_at, adjusted_amount, net_amount, "
                    "derived_status FROM internship_management.v_payment_status "
                    "WHERE enrollment_id = :enrollment_id "
                    "ORDER BY paid_at DESC, payment_id DESC "
                    "OFFSET :offset LIMIT :limit"
                ),
                {
                    "enrollment_id": enrollment_id,
                    "offset": (page - 1) * page_size,
                    "limit": page_size,
                },
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows], count

    def get_payment_status(self, payment_id: int) -> dict | None:
        row = (
            self.session.execute(
                text(
                    "SELECT payment_id, enrollment_id, amount, currency, paid_at, payment_method, "
                    "payment_reference, recorded_by, created_at, adjusted_amount, net_amount, "
                    "derived_status FROM internship_management.v_payment_status "
                    "WHERE payment_id = :payment_id"
                ),
                {"payment_id": payment_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def list_payment_adjustments(self, payment_id: int) -> list[PaymentAdjustment]:
        return list(
            self.session.scalars(
                select(PaymentAdjustment)
                .where(PaymentAdjustment.payment_id == payment_id)
                .order_by(PaymentAdjustment.occurred_at, PaymentAdjustment.adjustment_id)
            ).all()
        )

    def adjusted_amount_for_payment(self, payment_id: int):
        return self.session.scalar(
            select(func.coalesce(func.sum(PaymentAdjustment.amount), 0)).where(
                PaymentAdjustment.payment_id == payment_id
            )
        )
