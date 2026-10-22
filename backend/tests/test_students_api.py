from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models.admin import Admin
from app.models.student import Student
from app.security import hash_password


@pytest.fixture
def admin_auth_headers(api_client, db_session) -> dict[str, str]:
    username = f"students-{uuid4().hex}"
    db_session.add(
        Admin(
            username=username,
            password_hash=hash_password("Student-test-password-123!"),
            is_active=True,
        )
    )
    db_session.commit()
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Student-test-password-123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.integration
def test_students_api_requires_admin(api_client) -> None:
    assert api_client.get("/api/v1/students").status_code == 401
    assert api_client.post(
        "/api/v1/students",
        json={"full_name": "Test Student"},
    ).status_code == 401
    assert api_client.get("/api/v1/students/1").status_code == 401
    assert api_client.patch("/api/v1/students/1", json={"full_name": "Updated"}).status_code == 401


@pytest.mark.integration
def test_create_retrieve_and_update_student(api_client, admin_auth_headers) -> None:
    email = f"{uuid4().hex[:12]}@example.com"
    created = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "full_name": "  Asha Example  ",
            "email": email,
            "phone": " +91 90000 00000 ",
            "course": " BCA ",
            "institution_name": " Example College ",
        },
    )
    assert created.status_code == 201
    student = created.json()
    assert student["student_number"].startswith("STU-")
    assert student["full_name"] == "Asha Example"
    assert student["course"] == "BCA"
    assert student["institution_name"] == "Example College"
    assert student["status"] == "active"
    assert student["archived_at"] is None
    assert "password_hash" not in student

    retrieved = api_client.get(
        f"/api/v1/students/{student['student_id']}", headers=admin_auth_headers
    )
    assert retrieved.status_code == 200
    assert retrieved.json() == student

    updated = api_client.patch(
        f"/api/v1/students/{student['student_id']}",
        headers=admin_auth_headers,
        json={
            "full_name": "Asha Updated",
            "status": "archived",
            "reason": "Student completed records review",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Asha Updated"
    assert updated.json()["status"] == "archived"
    assert updated.json()["archived_at"] is not None


@pytest.mark.integration
def test_student_generated_numbers_are_unique_and_emails_are_case_insensitive(
    api_client, admin_auth_headers
) -> None:
    email = f"duplicate-{uuid4().hex}@example.com"
    first = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"full_name": "First Student", "email": email},
    )
    assert first.status_code == 201

    second = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"full_name": "Second Student"},
    )
    duplicate_email = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"full_name": "Duplicate Email", "email": email.upper()},
    )
    assert second.status_code == 201
    assert second.json()["student_number"] != first.json()["student_number"]
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["code"] == "duplicate_student_email"


@pytest.mark.integration
def test_student_search_status_filter_and_pagination(api_client, admin_auth_headers) -> None:
    marker = uuid4().hex[:10]
    created_ids: list[int] = []
    for index in range(3):
        response = api_client.post(
            "/api/v1/students",
            headers=admin_auth_headers,
            json={
                "full_name": f"Searchable {marker} {index}",
            },
        )
        assert response.status_code == 201
        created_ids.append(response.json()["student_id"])

    archived = api_client.patch(
        f"/api/v1/students/{created_ids[0]}",
        headers=admin_auth_headers,
        json={"status": "archived", "reason": "Student completed program"},
    )
    assert archived.status_code == 200

    first_page = api_client.get(
        f"/api/v1/students?q={marker}&page=1&page_size=2&status=all",
        headers=admin_auth_headers,
    )
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert first_page.json()["pages"] == 2
    assert len(first_page.json()["items"]) == 2

    archived_page = api_client.get(
        f"/api/v1/students?q={marker}&status=archived",
        headers=admin_auth_headers,
    )
    assert archived_page.status_code == 200
    assert archived_page.json()["total"] == 1


@pytest.mark.integration
def test_student_validation_and_delete_requires_reason(api_client, admin_auth_headers) -> None:
    invalid = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"full_name": ""},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"

    spoofed_creator = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "full_name": "Spoofed Creator",
            "student_number": f"STU-{uuid4().hex}",
            "created_by": 999999,
            "status": "archived",
            "reason": "Not allowed",
        },
    )
    assert spoofed_creator.status_code == 422

    missing_reason = api_client.delete(
        "/api/v1/students/123", headers=admin_auth_headers, json={}
    )
    assert missing_reason.status_code == 422


@pytest.mark.integration
def test_student_creation_with_batch_creates_enrollment_and_initial_fee_atomically(
    api_client, admin_auth_headers
) -> None:
    program = api_client.post(
        "/api/v1/programs",
        headers=admin_auth_headers,
        json={"name": f"Batch workflow {uuid4().hex[:8]}", "duration_months": 3, "status": "active"},
    ).json()
    starts_on = date.today() + timedelta(days=1)
    ends_on = starts_on + timedelta(days=60)
    batch_response = api_client.post(
        "/api/v1/batches",
        headers=admin_auth_headers,
        json={
            "program_id": program["program_id"],
            "name": f"Workflow batch {uuid4().hex[:8]}",
            "starts_on": starts_on.isoformat(),
            "ends_on": ends_on.isoformat(),
            "capacity": 2,
        },
    )
    assert batch_response.status_code == 201
    batch = batch_response.json()
    email = f"{uuid4().hex[:12]}@example.com"
    created = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "full_name": "Batch Enrolled Student",
            "email": email,
            "program_id": program["program_id"],
            "batch_id": batch["batch_id"],
            "agreed_fee_amount": "15000.00",
        },
    )
    assert created.status_code == 201
    student = created.json()

    enrollments = api_client.get(
        f"/api/v1/enrollments?student_id={student['student_id']}&status=all",
        headers=admin_auth_headers,
    )
    assert enrollments.status_code == 200
    enrollment = enrollments.json()["items"][0]
    assert enrollment["batch_id"] == batch["batch_id"]
    assert enrollment["program_id"] == program["program_id"]

    fees = api_client.get(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/fees",
        headers=admin_auth_headers,
    )
    assert fees.status_code == 200
    assert fees.json()["effective_fee"] == "15000.00"
    assert fees.json()["pending_balance"] == "15000.00"

    listed_batch = api_client.get(
        f"/api/v1/batches?program_id={program['program_id']}&status=all",
        headers=admin_auth_headers,
    ).json()["items"][0]
    assert listed_batch["program_name"] == program["name"]
    assert listed_batch["program_code"] == program["program_code"]
    assert listed_batch["enrollment_count"] == 1
    assert listed_batch["active_enrollment_count"] == 1
    assert listed_batch["unique_active_student_count"] == 1

    roster = api_client.get(
        f"/api/v1/batches/{batch['batch_id']}/students?status=active&q={student['student_number']}",
        headers=admin_auth_headers,
    )
    assert roster.status_code == 200
    assert roster.json()["total"] == 1
    roster_student = roster.json()["students"][0]
    assert roster_student["student_id"] == student["student_id"]
    assert roster_student["enrollment_number"] == enrollment["enrollment_number"]
    assert roster_student["fee_summary"]["pending_balance"] == "15000.00"

    cancelled = api_client.patch(
        f"/api/v1/enrollments/{enrollment['enrollment_id']}/status",
        headers=admin_auth_headers,
        json={"status": "cancelled", "reason": "Intake was cancelled"},
    )
    assert cancelled.status_code == 200
    cancelled_roster = api_client.get(
        f"/api/v1/batches/{batch['batch_id']}/students?status=cancelled",
        headers=admin_auth_headers,
    )
    assert cancelled_roster.status_code == 200
    assert cancelled_roster.json()["total"] == 1
    assert cancelled_roster.json()["active_enrollment_count"] == 0
    assert cancelled_roster.json()["unique_active_student_count"] == 0

    filtered_students = api_client.get(
        "/api/v1/students"
        f"?batch_id={batch['batch_id']}&program_id={program['program_id']}"
        "&enrollment_status=cancelled&fee_status=outstanding&status=all",
        headers=admin_auth_headers,
    )
    assert filtered_students.status_code == 200
    assert filtered_students.json()["total"] == 1


@pytest.mark.integration
def test_student_batch_mismatch_and_fee_term_failure_leave_no_partial_student(
    api_client, admin_auth_headers, db_session, monkeypatch
) -> None:
    program_a = api_client.post(
        "/api/v1/programs",
        headers=admin_auth_headers,
        json={"name": f"Program A {uuid4().hex[:8]}", "duration_months": 3, "status": "active"},
    ).json()
    program_b = api_client.post(
        "/api/v1/programs",
        headers=admin_auth_headers,
        json={"name": f"Program B {uuid4().hex[:8]}", "duration_months": 3, "status": "active"},
    ).json()
    starts_on = date.today() + timedelta(days=1)
    batch = api_client.post(
        "/api/v1/batches",
        headers=admin_auth_headers,
        json={
            "program_id": program_a["program_id"],
            "name": f"Mismatch batch {uuid4().hex[:8]}",
            "starts_on": starts_on.isoformat(),
            "ends_on": (starts_on + timedelta(days=60)).isoformat(),
        },
    ).json()
    mismatch_email = f"{uuid4().hex[:12]}@example.com"
    mismatch = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "full_name": "Wrong Program Student",
            "email": mismatch_email,
            "program_id": program_b["program_id"],
            "batch_id": batch["batch_id"],
            "agreed_fee_amount": "10000.00",
        },
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "program_batch_mismatch"
    assert db_session.scalar(select(func.count()).select_from(Student).where(Student.email == mismatch_email)) == 0

    import app.services.student_service as student_service

    def fail_fee_term(**_kwargs):
        raise __import__("sqlalchemy").exc.IntegrityError(
            "synthetic fee-term failure", {}, RuntimeError("test failure")
        )

    monkeypatch.setattr(student_service, "EnrollmentFeeTerm", fail_fee_term)
    rollback_email = f"{uuid4().hex[:12]}@example.com"
    failed = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "full_name": "Rollback Student",
            "email": rollback_email,
            "program_id": program_a["program_id"],
            "batch_id": batch["batch_id"],
            "agreed_fee_amount": "10000.00",
        },
    )
    assert failed.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Student).where(Student.email == rollback_email)) == 0