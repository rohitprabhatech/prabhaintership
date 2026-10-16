from uuid import uuid4

import pytest

from app.models.admin import Admin
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
        json={"student_number": "S-1", "full_name": "Test Student"},
    ).status_code == 401
    assert api_client.get("/api/v1/students/1").status_code == 401
    assert api_client.patch("/api/v1/students/1", json={"full_name": "Updated"}).status_code == 401


@pytest.mark.integration
def test_create_retrieve_and_update_student(api_client, admin_auth_headers) -> None:
    student_number = f"S-{uuid4().hex[:12]}"
    created = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "student_number": f" {student_number} ",
            "full_name": "  Asha Example  ",
            "email": f"{student_number}@example.com",
            "phone": " +91 90000 00000 ",
        },
    )
    assert created.status_code == 201
    student = created.json()
    assert student["student_number"] == student_number
    assert student["full_name"] == "Asha Example"
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
        json={"full_name": "Asha Updated", "status": "archived"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Asha Updated"
    assert updated.json()["status"] == "archived"
    assert updated.json()["archived_at"] is not None


@pytest.mark.integration
def test_student_duplicate_checks_are_case_insensitive_for_email(
    api_client, admin_auth_headers
) -> None:
    email = f"duplicate-{uuid4().hex}@example.com"
    first = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"student_number": f"A-{uuid4().hex}", "full_name": "First Student", "email": email},
    )
    assert first.status_code == 201

    duplicate_number = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "student_number": first.json()["student_number"],
            "full_name": "Duplicate Number",
        },
    )
    duplicate_email = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "student_number": f"B-{uuid4().hex}",
            "full_name": "Duplicate Email",
            "email": email.upper(),
        },
    )
    assert duplicate_number.status_code == 409
    assert duplicate_number.json()["code"] == "duplicate_student_number"
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
                "student_number": f"{marker}-{index}",
                "full_name": f"Searchable {marker} {index}",
            },
        )
        assert response.status_code == 201
        created_ids.append(response.json()["student_id"])

    archived = api_client.patch(
        f"/api/v1/students/{created_ids[0]}",
        headers=admin_auth_headers,
        json={"status": "archived"},
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
def test_student_validation_and_no_delete_route(api_client, admin_auth_headers) -> None:
    invalid = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={"student_number": " ", "full_name": ""},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"

    spoofed_creator = api_client.post(
        "/api/v1/students",
        headers=admin_auth_headers,
        json={
            "student_number": f"S-{uuid4().hex}",
            "full_name": "Spoofed Creator",
            "created_by": 999999,
            "status": "archived",
        },
    )
    assert spoofed_creator.status_code == 422

    deleted = api_client.delete("/api/v1/students/123", headers=admin_auth_headers)
    assert deleted.status_code == 405