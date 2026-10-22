from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.batch_service as batch_service
from app.api.deps import get_current_admin
from app.db.session import get_db
from app.main import app


def test_batch_list_endpoint_maps_program_and_count_fields(monkeypatch) -> None:
    batch = SimpleNamespace(
        batch_id=7,
        program_id=3,
        batch_code="BAT-2026-0001",
        name="Python Cohort",
        starts_on=date(2026, 11, 1),
        ends_on=date(2027, 1, 31),
        capacity=25,
        status="active",
        created_by=1,
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    repository = SimpleNamespace(
        rows=[
            (batch, "Python Internship", "PRG-2026-0001", 4, 3, 2),
        ]
    )

    class FakeBatchRepository:
        def __init__(self, _session) -> None:
            pass

        def list(self, **_kwargs):
            return repository.rows, 1

    monkeypatch.setattr(batch_service, "BatchRepository", FakeBatchRepository)
    monkeypatch.setitem(app.dependency_overrides, get_current_admin, lambda: object())
    monkeypatch.setitem(app.dependency_overrides, get_db, lambda: object())

    with TestClient(app) as client:
        response = client.get("/api/v1/batches?status=active&page=1&page_size=1")
        assert response.status_code == 200
        listed = response.json()["items"][0]
        assert listed["program_name"] == "Python Internship"
        assert listed["program_code"] == "PRG-2026-0001"
        assert listed["enrollment_count"] == 4
        assert listed["active_enrollment_count"] == 3
        assert listed["unique_active_student_count"] == 2

        repository.rows = [(batch, None, None, 0, 0, 0)]
        invalid_relationship = client.get("/api/v1/batches?status=active&page=1&page_size=1")
        assert invalid_relationship.status_code == 500
        assert invalid_relationship.json()["code"] == "batch_program_integrity_error"
