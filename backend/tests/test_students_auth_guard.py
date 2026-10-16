import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


@pytest.fixture
def no_database_client():
    def no_database_dependency():
        yield None

    app.dependency_overrides[get_db] = no_database_dependency
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/students", None),
        ("post", "/api/v1/students", {"student_number": "PT-1", "full_name": "Test"}),
        ("get", "/api/v1/students/1", None),
        ("patch", "/api/v1/students/1", {"full_name": "Updated"}),
    ],
)
def test_every_student_operation_requires_admin(
    no_database_client, method: str, path: str, payload: dict | None
) -> None:
    response = getattr(no_database_client, method)(path, json=payload) if payload else getattr(
        no_database_client, method
    )(path)

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_student_delete_route_is_not_registered(no_database_client) -> None:
    response = no_database_client.delete("/api/v1/students/1")

    assert response.status_code == 405