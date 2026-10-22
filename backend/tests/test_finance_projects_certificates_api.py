from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models.payment import Payment
from app.schemas.finance import FeeAdjustmentCreate, PaymentCreate


@pytest.fixture
def admin_headers(api_client, db_session) -> dict[str, str]:
    from app.models.admin import Admin
    from app.security import hash_password

    username = f"sprint5-{uuid4().hex}"
    db_session.add(
        Admin(
            username=username,
            password_hash=hash_password("Sprint-five-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Sprint-five-test-password-123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_program(api_client, headers: dict[str, str]) -> dict:
    response = api_client.post(
        "/api/v1/programs",
        headers=headers,
        json={"name": f"Program {uuid4().hex[:10]}", "duration_months": 3, "status": "active"},
    )
    assert response.status_code == 201
    return response.json()


def create_student(api_client, headers: dict[str, str]) -> dict:
    response = api_client.post(
        "/api/v1/students",
        headers=headers,
        json={"full_name": f"Student {uuid4().hex[:10]}"},
    )
    assert response.status_code == 201
    return response.json()


def create_enrollment(
    api_client,
    headers: dict[str, str],
    *,
    amount: str = "10000.00",
    capacity: int | None = None,
) -> tuple[dict, dict, dict]:
    program = create_program(api_client, headers)
    student = create_student(api_client, headers)
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=60)
    batch_response = api_client.post(
        "/api/v1/batches",
        headers=headers,
        json={
            "program_id": program["program_id"],
            "name": f"Batch {uuid4().hex[:8]}",
            "starts_on": start.isoformat(),
            "ends_on": end.isoformat(),
            "capacity": capacity,
        },
    )
    assert batch_response.status_code == 201
    batch = batch_response.json()
    enrollment_response = api_client.post(
        "/api/v1/enrollments",
        headers=headers,
        json={
            "student_id": student["student_id"],
            "batch_id": batch["batch_id"],
            "starts_on": start.isoformat(),
            "ends_on": end.isoformat(),
            "agreed_fee_amount": amount,
            "fee_reason": "Approved initial fee",
        },
    )
    assert enrollment_response.status_code == 201, enrollment_response.text
    return program, batch, enrollment_response.json()


def post_payment(api_client, headers, enrollment_id: int, amount: str, key=None):
    return api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/payments",
        headers={
            **headers,
            "Idempotency-Key": str(key or uuid4()),
        },
        json={"amount": amount, "payment_method": "upi"},
    )


@pytest.mark.integration
def test_partial_and_full_installment_payment_summary(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    enrollment_id = enrollment["enrollment_id"]

    partial = post_payment(api_client, admin_headers, enrollment_id, "2500.00")
    assert partial.status_code == 201
    assert partial.json()["amount"] == "2500.00"
    assert partial.json()["derived_status"] == "posted"
    summary = api_client.get(f"/api/v1/enrollments/{enrollment_id}/fees", headers=admin_headers)
    assert summary.status_code == 200
    assert summary.json()["net_paid"] == "2500.00"
    assert summary.json()["pending_balance"] == "7500.00"

    final = post_payment(api_client, admin_headers, enrollment_id, "7500.00")
    assert final.status_code == 201
    summary = api_client.get(f"/api/v1/enrollments/{enrollment_id}/fees", headers=admin_headers)
    assert summary.json()["net_paid"] == "10000.00"
    assert summary.json()["pending_balance"] == "0.00"
    history = api_client.get(
        f"/api/v1/enrollments/{enrollment_id}/payments?page=1&page_size=10",
        headers=admin_headers,
    )
    assert history.status_code == 200
    assert history.json()["total"] == 2


@pytest.mark.integration
def test_overpayment_and_non_cent_precision_are_rejected(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    enrollment_id = enrollment["enrollment_id"]
    overpayment = post_payment(api_client, admin_headers, enrollment_id, "10000.01")
    assert overpayment.status_code == 409
    assert overpayment.json()["code"] == "overpayment_rejected"

    invalid_precision = post_payment(api_client, admin_headers, enrollment_id, "1.001")
    assert invalid_precision.status_code == 422
    invalid_zero = post_payment(api_client, admin_headers, enrollment_id, "0.00")
    assert invalid_zero.status_code == 422


@pytest.mark.integration
def test_payment_rejects_invalid_enrollment_and_requires_admin(api_client, admin_headers) -> None:
    payload = {"amount": "1.00", "payment_method": "upi"}
    key = str(uuid4())

    unauthorized = api_client.post(
        "/api/v1/enrollments/999999/payments",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    assert unauthorized.status_code == 401

    missing_enrollment = api_client.post(
        "/api/v1/enrollments/999999/payments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json=payload,
    )
    assert missing_enrollment.status_code == 404
    assert missing_enrollment.json()["code"] == "enrollment_not_found"


@pytest.mark.integration
def test_payment_reference_conflict_rolls_back_insert(
    api_client, admin_headers, db_session
) -> None:
    _, _, first_enrollment = create_enrollment(api_client, admin_headers)
    _, _, second_enrollment = create_enrollment(api_client, admin_headers)
    reference = f"QA-{uuid4().hex}"

    first = api_client.post(
        f"/api/v1/enrollments/{first_enrollment['enrollment_id']}/payments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={
            "amount": "100.00",
            "payment_method": "upi",
            "payment_reference": reference,
        },
    )
    assert first.status_code == 201

    duplicate = api_client.post(
        f"/api/v1/enrollments/{second_enrollment['enrollment_id']}/payments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={
            "amount": "100.00",
            "payment_method": "upi",
            "payment_reference": reference,
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "payment_conflict"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.enrollment_id == second_enrollment["enrollment_id"])
        )
        == 0
    )


@pytest.mark.integration
def test_repeated_payment_request_is_idempotent(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    key = uuid4()
    first = post_payment(api_client, admin_headers, enrollment["enrollment_id"], "1250.00", key)
    retry = post_payment(api_client, admin_headers, enrollment["enrollment_id"], "1250.00", key)

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["payment_id"] == first.json()["payment_id"]
    summary = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/fees", headers=admin_headers
    )
    assert summary.json()["net_paid"] == "1250.00"

    reused_key = post_payment(
        api_client, admin_headers, enrollment["enrollment_id"], "1500.00", key
    )
    assert reused_key.status_code == 409
    assert reused_key.json()["code"] == "idempotency_key_reused"


@pytest.mark.integration
def test_concurrent_payments_cannot_overpay_enrollment(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)

    def submit(amount: str):
        return post_payment(api_client, admin_headers, enrollment["enrollment_id"], amount)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, ["6000.00", "6000.00"]))

    assert sorted(response.status_code for response in results) == [201, 409]
    summary = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/fees", headers=admin_headers
    )
    assert Decimal(summary.json()["net_paid"]) == Decimal("6000.00")
    assert Decimal(summary.json()["pending_balance"]) == Decimal("4000.00")


@pytest.mark.integration
def test_approved_discount_refund_and_adjustment_history(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    enrollment_id = enrollment["enrollment_id"]
    discount_key = uuid4()
    discount_payload = {
        "adjustment_type": "discount",
        "amount": "2000.00",
        "reason": "Approved scholarship",
    }
    discount = api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/fee-adjustments",
        headers={**admin_headers, "Idempotency-Key": str(discount_key)},
        json=discount_payload,
    )
    replay = api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/fee-adjustments",
        headers={**admin_headers, "Idempotency-Key": str(discount_key)},
        json=discount_payload,
    )
    assert discount.status_code == 201
    assert replay.status_code == 200
    summary = api_client.get(f"/api/v1/enrollments/{enrollment_id}/fees", headers=admin_headers)
    assert summary.json()["effective_fee"] == "8000.00"

    payment = post_payment(api_client, admin_headers, enrollment_id, "4000.00")
    adjustment = api_client.post(
        f"/api/v1/payments/{payment.json()['payment_id']}/adjustments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={"adjustment_type": "refund", "amount": "1000.00", "reason": "Approved refund"},
    )
    assert payment.status_code == 201
    assert adjustment.status_code == 201
    refreshed = api_client.get(f"/api/v1/enrollments/{enrollment_id}/fees", headers=admin_headers)
    assert refreshed.json()["net_paid"] == "3000.00"
    assert refreshed.json()["pending_balance"] == "5000.00"


@pytest.mark.integration
def test_refund_cannot_exceed_receipt_and_reversal_must_be_full(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    payment = post_payment(api_client, admin_headers, enrollment["enrollment_id"], "3000.00")
    payment_id = payment.json()["payment_id"]

    excess = api_client.post(
        f"/api/v1/payments/{payment_id}/adjustments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={"adjustment_type": "refund", "amount": "3000.01", "reason": "Excess"},
    )
    partial_reversal = api_client.post(
        f"/api/v1/payments/{payment_id}/adjustments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={"adjustment_type": "reversal", "amount": "1000.00", "reason": "Wrong receipt"},
    )
    assert excess.status_code == 409
    assert partial_reversal.status_code == 422


@pytest.mark.integration
def test_fee_adjustments_and_revision_preserve_one_current_term(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    enrollment_id = enrollment["enrollment_id"]

    for adjustment_type, amount in (("discount", "1000.00"), ("fee_increase", "500.00")):
        response = api_client.post(
            f"/api/v1/enrollments/{enrollment_id}/fee-adjustments",
            headers={**admin_headers, "Idempotency-Key": str(uuid4())},
            json={
                "adjustment_type": adjustment_type,
                "amount": amount,
                "reason": f"Approved {adjustment_type}",
            },
        )
        assert response.status_code == 201

    payment = post_payment(api_client, admin_headers, enrollment_id, "2500.00")
    assert payment.status_code == 201

    revision = api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/fee-terms",
        headers=admin_headers,
        json={"agreed_amount": "9000.00", "reason": "Approved revised fee"},
    )
    assert revision.status_code == 201
    terms = api_client.get(
        f"/api/v1/enrollments/{enrollment_id}/fee-terms", headers=admin_headers
    )
    assert terms.status_code == 200
    assert len(terms.json()) == 2
    assert sum(term["effective_to"] is None for term in terms.json()) == 1

    invalid_revision = api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/fee-terms",
        headers=admin_headers,
        json={"agreed_amount": "2000.00", "reason": "Below net payments"},
    )
    assert invalid_revision.status_code == 409
    after_rejection = api_client.get(
        f"/api/v1/enrollments/{enrollment_id}/fee-terms", headers=admin_headers
    )
    assert len(after_rejection.json()) == 2
    assert sum(term["effective_to"] is None for term in after_rejection.json()) == 1


@pytest.mark.integration
def test_partial_refund_then_full_remaining_reversal_updates_balance(
    api_client, admin_headers
) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    payment = post_payment(api_client, admin_headers, enrollment["enrollment_id"], "4000.00")
    payment_id = payment.json()["payment_id"]

    refund = api_client.post(
        f"/api/v1/payments/{payment_id}/adjustments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={"adjustment_type": "refund", "amount": "1000.00", "reason": "Partial refund"},
    )
    reversal = api_client.post(
        f"/api/v1/payments/{payment_id}/adjustments",
        headers={**admin_headers, "Idempotency-Key": str(uuid4())},
        json={"adjustment_type": "reversal", "amount": "3000.00", "reason": "Reverse remainder"},
    )
    assert refund.status_code == 201
    assert reversal.status_code == 201

    payments = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/payments?page=1&page_size=10",
        headers=admin_headers,
    )
    assert payments.status_code == 200
    assert payments.json()["items"][0]["derived_status"] == "reversed"
    assert payments.json()["items"][0]["net_amount"] == "0.00"
    summary = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/fees", headers=admin_headers
    )
    assert summary.json()["net_paid"] == "0.00"
    assert summary.json()["pending_balance"] == "10000.00"


@pytest.mark.integration
def test_project_assignment_completion_and_certificate_lifecycle(api_client, admin_headers) -> None:
    _, _, enrollment = create_enrollment(api_client, admin_headers)
    enrollment_id = enrollment["enrollment_id"]
    project_response = api_client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={"name": "Inventory API"},
    )
    assert project_response.status_code == 201
    project = project_response.json()
    assert project["project_code"].startswith("PRJ-")
    assigned = api_client.post(
        f"/api/v1/enrollments/{enrollment_id}/projects",
        headers=admin_headers,
        json={"project_id": project["project_id"]},
    )
    assert assigned.status_code == 201
    dependencies = api_client.get(
        f"/api/v1/projects/{project['project_id']}/dependencies", headers=admin_headers
    )
    assert dependencies.status_code == 200
    assert dependencies.json()["can_delete"] is False
    blocked_delete = api_client.delete(
        f"/api/v1/projects/{project['project_id']}",
        headers=admin_headers,
        json={"reason": "Retain assignment history"},
    )
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["code"] == "project_has_history"
    progressing = api_client.patch(
        f"/api/v1/project-assignments/{assigned.json()['project_assignment_id']}/status",
        headers=admin_headers,
        json={"status": "in_progress"},
    )
    completed = api_client.patch(
        f"/api/v1/project-assignments/{assigned.json()['project_assignment_id']}/status",
        headers=admin_headers,
        json={"status": "completed"},
    )
    assert progressing.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    archived = api_client.patch(
        f"/api/v1/projects/{project['project_id']}/status",
        headers=admin_headers,
        json={"status": "archived", "reason": "Project delivery archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    certificate = api_client.post(
        "/api/v1/certificates",
        headers=admin_headers,
        json={
            "enrollment_id": enrollment_id,
            "certificate_type": "completion",
        },
    )
    assert certificate.status_code == 201
    assert certificate.json()["certificate_number"].startswith("CERT-")
    certificate_id = certificate.json()["certificate_id"]
    replacement = api_client.post(
        f"/api/v1/certificates/{certificate_id}/replacement",
        headers=admin_headers,
        json={"reason": "Corrected spelling"},
    )
    assert replacement.status_code == 201
    assert replacement.json()["certificate_number"].startswith("CERT-")
    assert replacement.json()["certificate_number"] != certificate.json()["certificate_number"]
    original_status = api_client.get(
        f"/api/v1/certificates/{certificate_id}", headers=admin_headers
    )
    assert original_status.json()["derived_status"] == "replaced"
    immutable_update = api_client.patch(
        f"/api/v1/certificates/{certificate_id}",
        headers=admin_headers,
        json={"certificate_number": "OVERWRITE"},
    )
    assert immutable_update.status_code == 405

    report = api_client.get("/api/v1/certificates?status=issued", headers=admin_headers)
    assert report.status_code == 200
    assert any(
        item["certificate_id"] == replacement.json()["certificate_id"]
        for item in report.json()["items"]
    )


@pytest.mark.integration
def test_finance_project_and_certificate_endpoints_require_admin(api_client) -> None:
    assert api_client.get("/api/v1/projects").status_code == 401
    assert api_client.post("/api/v1/projects", json={}).status_code == 401
    assert api_client.get("/api/v1/project-assignments").status_code == 401
    assert api_client.post("/api/v1/certificates", json={}).status_code == 401
    assert api_client.get("/api/v1/certificates").status_code == 401


def test_money_schemas_reject_zero_negative_and_sub_cent_values() -> None:
    for amount in ("0.00", "-1.00", "1.001"):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=amount, payment_method="upi")
        with pytest.raises(ValidationError):
            FeeAdjustmentCreate(
                adjustment_type="discount",
                amount=amount,
                reason="Invalid amount",
            )
