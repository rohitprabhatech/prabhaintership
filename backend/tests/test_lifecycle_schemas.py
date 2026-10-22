import pytest
from pydantic import ValidationError

from app.schemas.batch import BatchUpdate
from app.schemas.enrollment import EnrollmentStatusUpdate
from app.schemas.finance import ProjectAssignmentStatusUpdate, ProjectStatusUpdate
from app.schemas.lifecycle import ReasonRequest
from app.schemas.program import ProgramUpdate
from app.schemas.student import StudentUpdate


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (StudentUpdate, {"status": "archived"}),
        (ProgramUpdate, {"status": "inactive"}),
        (BatchUpdate, {"status": "cancelled"}),
        (EnrollmentStatusUpdate, {"status": "cancelled"}),
        (EnrollmentStatusUpdate, {"status": "withdrawn"}),
        (ProjectAssignmentStatusUpdate, {"status": "cancelled"}),
        (ProjectStatusUpdate, {"status": "archived"}),
    ],
)
def test_sensitive_lifecycle_action_requires_reason(schema, payload: dict) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
    with pytest.raises(ValidationError):
        schema.model_validate({**payload, "reason": "   "})


def test_lifecycle_reasons_are_trimmed_and_bounded() -> None:
    assert ReasonRequest(reason="  approved data cleanup  ").reason == "approved data cleanup"
    with pytest.raises(ValidationError):
        ReasonRequest(reason=" " * 3)
