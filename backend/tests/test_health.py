from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, create_app


def test_liveness_does_not_require_database() -> None:
    response = TestClient(app).get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-request-id")


def test_unknown_routes_use_safe_error_shape() -> None:
    response = TestClient(app).get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json()["code"] == "http_error"
    assert "detail" not in response.json()


def test_unconfigured_cors_origin_is_not_allowed() -> None:
    response = TestClient(app).options(
        "/api/v1/health/live",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_trusted_origin_can_preflight_patch(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        db_name="internship_management_test",
        db_user="test",
        db_password="test-only-password",
        jwt_secret_key="test-only-secret-value-not-for-production-0123456789",
        cors_origins=["http://admin.example.test"],
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    test_app = create_app()

    response = TestClient(test_app).options(
        "/api/v1/students/1",
        headers={
            "Origin": "http://admin.example.test",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://admin.example.test"
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_trusted_origin_can_preflight_idempotency_header(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        db_name="internship_management_test",
        db_user="test",
        db_password="test-only-password",
        jwt_secret_key="test-only-secret-value-not-for-production-0123456789",
        cors_origins=["http://admin.example.test"],
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    test_app = create_app()

    response = TestClient(test_app).options(
        "/api/v1/enrollments/1/payments",
        headers={
            "Origin": "http://admin.example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )

    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def test_validation_error_does_not_echo_submitted_password() -> None:
    submitted_password = "must-not-appear-in-error-response"
    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"password": submitted_password},
    )

    assert response.status_code == 422
    assert submitted_password not in response.text
    assert response.json()["code"] == "validation_error"
