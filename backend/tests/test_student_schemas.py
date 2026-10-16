import pytest
from pydantic import ValidationError

from app.schemas.student import StudentCreate, StudentUpdate


def test_student_create_trims_text_and_rejects_server_managed_fields() -> None:
    student = StudentCreate(
        student_number=" PT-2026-0042 ",
        full_name=" Asha Patel ",
        email="asha.patel@example.com",
        phone=" +91 98765 43210 ",
    )

    assert student.student_number == "PT-2026-0042"
    assert student.full_name == "Asha Patel"
    assert student.phone == "+91 98765 43210"
    with pytest.raises(ValidationError):
        StudentCreate.model_validate(
            {
                "student_number": "PT-2026-0043",
                "full_name": "Asha Patel",
                "created_by": 999,
                "status": "archived",
            }
        )


def test_student_create_rejects_blank_and_invalid_email() -> None:
    with pytest.raises(ValidationError):
        StudentCreate(student_number=" ", full_name="Asha Patel")
    with pytest.raises(ValidationError):
        StudentCreate(student_number="PT-2026-0042", full_name="Asha Patel", email="not-an-email")


def test_student_update_requires_editable_fields_and_rejects_null_identity() -> None:
    with pytest.raises(ValidationError):
        StudentUpdate.model_validate({})
    with pytest.raises(ValidationError):
        StudentUpdate.model_validate({"full_name": None})
    assert StudentUpdate.model_validate({"email": None}).model_fields_set == {"email"}