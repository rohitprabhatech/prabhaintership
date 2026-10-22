import pytest
from pydantic import ValidationError

from app.schemas.student import StudentCreate, StudentUpdate


def test_student_create_trims_profile_text_and_rejects_server_managed_fields() -> None:
    student = StudentCreate(
        full_name=" Asha Patel ",
        email="asha.patel@example.com",
        phone=" +91 98765 43210 ",
        institution_name=" Prabha College ",
        course=" BCA ",
        internship_domain=" Python Development ",
        city=" Pune ",
    )

    assert student.full_name == "Asha Patel"
    assert student.phone == "+91 98765 43210"
    assert student.institution_name == "Prabha College"
    assert student.course == "BCA"
    assert student.internship_domain == "Python Development"
    assert student.city == "Pune"
    with pytest.raises(ValidationError):
        StudentCreate.model_validate(
            {
                "full_name": "Asha Patel",
                "student_number": "STU-2026-000001",
                "created_by": 999,
                "status": "archived",
            }
        )


def test_student_create_allows_empty_optional_contact_and_rejects_invalid_email() -> None:
    assert StudentCreate(full_name="Asha Patel").email is None
    with pytest.raises(ValidationError):
        StudentCreate(full_name="Asha Patel", email="not-an-email")
    with pytest.raises(ValidationError):
        StudentCreate(full_name=" ")


def test_student_create_requires_complete_initial_enrollment_details() -> None:
    with pytest.raises(ValidationError):
        StudentCreate.model_validate({"full_name": "Asha Patel", "program_id": 1})
    with pytest.raises(ValidationError):
        StudentCreate.model_validate(
            {"full_name": "Asha Patel", "enrollment_starts_on": "2026-01-01"}
        )
    student = StudentCreate.model_validate(
        {
            "full_name": "Asha Patel",
            "program_id": 1,
            "batch_id": 2,
            "agreed_fee_amount": "12500.00",
        }
    )
    assert student.agreed_fee_amount == 12500


def test_student_update_requires_editable_fields_and_rejects_managed_fields() -> None:
    with pytest.raises(ValidationError):
        StudentUpdate.model_validate({})
    with pytest.raises(ValidationError):
        StudentUpdate.model_validate({"full_name": None})
    with pytest.raises(ValidationError):
        StudentUpdate.model_validate({"student_number": "STU-2026-000001"})
    assert StudentUpdate.model_validate({"email": None}).model_fields_set == {"email"}
