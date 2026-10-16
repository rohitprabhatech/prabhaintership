from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.models.admin import Admin
from app.security import hash_password


@pytest.fixture
def admin_headers(api_client, db_session) -> dict[str, str]:
    username = f"sprint4-{uuid4().hex}"
    db_session.add(
        Admin(
            username=username,
            password_hash=hash_password("Sprint-four-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Sprint-four-test-password-123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_program(api_client, headers: dict[str, str], *, status: str = "active") -> dict:
    code = f"P-{uuid4().hex[:12]}"
    response = api_client.post(
        "/api/v1/programs",
        headers=headers,
        json={"program_code": code, "name": f"Program {code}", "status": status},
    )
    assert response.status_code == 201
    return response.json()


def create_student(api_client, headers: dict[str, str]) -> dict:
    number = f"ST-{uuid4().hex[:12]}"
    response = api_client.post(
        "/api/v1/students",
        headers=headers,
        json={"student_number": number, "full_name": f"Student {number}"},
    )
    assert response.status_code == 201
    return response.json()


def create_batch(
    api_client,
    headers: dict[str, str],
    program_id: int,
    *,
    capacity: int | None = None,
    starts_on: date | None = None,
    ends_on: date | None = None,
) -> dict:
    start = starts_on or date.today() + timedelta(days=1)
    end = ends_on or start + timedelta(days=60)
    code = f"B-{uuid4().hex[:12]}"
    response = api_client.post(
        "/api/v1/batches",
        headers=headers,
        json={
            "program_id": program_id,
            "batch_code": code,
            "name": f"Batch {code}",
            "starts_on": start.isoformat(),
            "ends_on": end.isoformat(),
            "capacity": capacity,
        },
    )
    return response


def enroll_student(
    api_client, headers: dict[str, str], student_id: int, program_id: int, batch: dict
):
    return api_client.post(
        "/api/v1/enrollments",
        headers=headers,
        json={
            "enrollment_number": f"EN-{uuid4().hex[:12]}",
            "student_id": student_id,
            "program_id": program_id,
            "batch_id": batch["batch_id"],
            "starts_on": batch["starts_on"],
            "ends_on": batch["ends_on"],
            "agreed_fee_amount": "10000.00",
            "fee_reason": "Approved initial fee",
        },
    )


@pytest.mark.integration
def test_program_batch_enrollment_roster_and_status_workflow(api_client, admin_headers) -> None:
    program = create_program(api_client, admin_headers)
    student = create_student(api_client, admin_headers)
    batch_response = create_batch(api_client, admin_headers, program["program_id"], capacity=3)
    assert batch_response.status_code == 201
    batch = batch_response.json()

    program_list = api_client.get(
        f"/api/v1/programs?q={program['program_code']}&status=active",
        headers=admin_headers,
    )
    assert program_list.status_code == 200
    assert program_list.json()["total"] == 1
    assert (
        api_client.get(
            f"/api/v1/programs/{program['program_id']}", headers=admin_headers
        ).status_code
        == 200
    )
    updated_program = api_client.patch(
        f"/api/v1/programs/{program['program_id']}",
        headers=admin_headers,
        json={"name": "Updated Internship Program"},
    )
    assert updated_program.status_code == 200
    assert updated_program.json()["name"] == "Updated Internship Program"

    batch_list = api_client.get(
        f"/api/v1/batches?program_id={program['program_id']}&status=planned",
        headers=admin_headers,
    )
    assert batch_list.status_code == 200
    assert batch_list.json()["total"] == 1
    active_batch = api_client.patch(
        f"/api/v1/batches/{batch['batch_id']}",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert active_batch.status_code == 200
    assert (
        api_client.get(f"/api/v1/batches/{batch['batch_id']}", headers=admin_headers).status_code
        == 200
    )

    created_enrollment = enroll_student(
        api_client, admin_headers, student["student_id"], program["program_id"], batch
    )
    assert created_enrollment.status_code == 201
    enrollment = created_enrollment.json()
    assert enrollment["status"] == "active"
    assert enrollment["student_id"] == student["student_id"]
    assert enrollment["program_id"] == program["program_id"]

    detail = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}", headers=admin_headers
    )
    assert detail.status_code == 200
    listing = api_client.get(
        f"/api/v1/enrollments?batch_id={batch['batch_id']}&status=active&page=1&page_size=1",
        headers=admin_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert len(listing.json()["items"]) == 1

    roster = api_client.get(f"/api/v1/batches/{batch['batch_id']}/roster", headers=admin_headers)
    assert roster.status_code == 200
    assert roster.json()["active_enrollment_count"] == 1
    assert roster.json()["students"][0]["student_number"] == student["student_number"]

    completed = api_client.patch(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/status",
        headers=admin_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    invalid_reactivation = api_client.patch(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/status",
        headers=admin_headers,
        json={"status": "active"},
    )
    assert invalid_reactivation.status_code == 409
    assert invalid_reactivation.json()["code"] == "invalid_enrollment_status_transition"


@pytest.mark.integration
def test_program_batch_and_enrollment_authorization(api_client) -> None:
    assert api_client.get("/api/v1/programs").status_code == 401
    assert api_client.post("/api/v1/programs", json={}).status_code == 401
    assert api_client.get("/api/v1/batches").status_code == 401
    assert api_client.post("/api/v1/batches", json={}).status_code == 401
    assert api_client.get("/api/v1/enrollments").status_code == 401
    assert api_client.post("/api/v1/enrollments", json={}).status_code == 401


@pytest.mark.integration
def test_invalid_program_batch_student_and_dates_are_rejected(api_client, admin_headers) -> None:
    inactive_program = create_program(api_client, admin_headers, status="draft")
    rejected_batch = create_batch(api_client, admin_headers, inactive_program["program_id"])
    assert rejected_batch.status_code == 409
    assert rejected_batch.json()["code"] == "program_not_active"

    active_program = create_program(api_client, admin_headers)
    bad_program_batch = create_batch(api_client, admin_headers, 999999)
    assert bad_program_batch.status_code == 404
    assert bad_program_batch.json()["code"] == "program_not_found"

    invalid_range = api_client.post(
        "/api/v1/batches",
        headers=admin_headers,
        json={
            "program_id": active_program["program_id"],
            "batch_code": f"BAD-{uuid4().hex[:8]}",
            "name": "Bad dates",
            "starts_on": "2026-12-10",
            "ends_on": "2026-12-09",
        },
    )
    assert invalid_range.status_code == 422

    batch = create_batch(api_client, admin_headers, active_program["program_id"]).json()
    student = create_student(api_client, admin_headers)
    no_student = api_client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={
            "enrollment_number": f"EN-{uuid4().hex[:10]}",
            "student_id": 999999,
            "program_id": active_program["program_id"],
            "batch_id": batch["batch_id"],
            "starts_on": batch["starts_on"],
            "agreed_fee_amount": "10000.00",
        },
    )
    assert no_student.status_code == 404
    assert no_student.json()["code"] == "student_not_found"

    outside_batch = api_client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={
            "enrollment_number": f"EN-{uuid4().hex[:10]}",
            "student_id": student["student_id"],
            "program_id": active_program["program_id"],
            "batch_id": batch["batch_id"],
            "starts_on": "2099-01-01",
            "agreed_fee_amount": "10000.00",
        },
    )
    assert outside_batch.status_code == 422
    assert outside_batch.json()["code"] == "enrollment_outside_batch_dates"


@pytest.mark.integration
def test_enrollment_rejects_program_batch_mismatch_and_duplicate(api_client, admin_headers) -> None:
    program_a = create_program(api_client, admin_headers)
    program_b = create_program(api_client, admin_headers)
    batch_b = create_batch(api_client, admin_headers, program_b["program_id"]).json()
    student = create_student(api_client, admin_headers)

    mismatch = api_client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={
            "enrollment_number": f"EN-{uuid4().hex[:10]}",
            "student_id": student["student_id"],
            "program_id": program_a["program_id"],
            "batch_id": batch_b["batch_id"],
            "starts_on": batch_b["starts_on"],
            "agreed_fee_amount": "10000.00",
        },
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["code"] == "batch_program_mismatch"

    batch_a = create_batch(api_client, admin_headers, program_a["program_id"]).json()
    first = enroll_student(
        api_client, admin_headers, student["student_id"], program_a["program_id"], batch_a
    )
    duplicate = enroll_student(
        api_client, admin_headers, student["student_id"], program_a["program_id"], batch_a
    )
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "duplicate_active_enrollment"


@pytest.mark.integration
def test_batch_capacity_and_capacity_updates_are_enforced(api_client, admin_headers) -> None:
    program = create_program(api_client, admin_headers)
    batch = create_batch(api_client, admin_headers, program["program_id"], capacity=2).json()
    first_student = create_student(api_client, admin_headers)
    second_student = create_student(api_client, admin_headers)
    third_student = create_student(api_client, admin_headers)

    first = enroll_student(
        api_client, admin_headers, first_student["student_id"], program["program_id"], batch
    )
    second = enroll_student(
        api_client, admin_headers, second_student["student_id"], program["program_id"], batch
    )
    third = enroll_student(
        api_client, admin_headers, third_student["student_id"], program["program_id"], batch
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 409
    assert third.json()["code"] == "batch_capacity_reached"

    capacity_below_roster = api_client.patch(
        f"/api/v1/batches/{batch['batch_id']}", headers=admin_headers, json={"capacity": 1}
    )
    assert capacity_below_roster.status_code == 409
    assert capacity_below_roster.json()["code"] == "batch_capacity_below_enrollment_count"


@pytest.mark.integration
def test_enrollments_preserve_history_and_have_no_delete_route(api_client, admin_headers) -> None:
    program = create_program(api_client, admin_headers)
    student = create_student(api_client, admin_headers)
    batch = create_batch(api_client, admin_headers, program["program_id"]).json()
    enrollment = enroll_student(
        api_client, admin_headers, student["student_id"], program["program_id"], batch
    ).json()

    deleted = api_client.delete(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}", headers=admin_headers
    )
    assert deleted.status_code == 405
    still_present = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}", headers=admin_headers
    )
    assert still_present.status_code == 200
