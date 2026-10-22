import pytest
from pydantic import ValidationError

from app.schemas.batch import BatchCreate
from app.schemas.enrollment import EnrollmentCreate
from app.schemas.finance import CertificateIssueCreate, CertificateReplacementCreate, ProjectCreate
from app.schemas.program import ProgramCreate


def test_business_identifiers_are_not_client_editable() -> None:
    program = ProgramCreate(name=" Python Internship ", duration_months=3)
    assert program.name == "Python Internship"
    with pytest.raises(ValidationError):
        ProgramCreate(
            name="Python Internship",
            duration_months=3,
            program_code="PRG-2026-0001",
        )

    batch = BatchCreate(
        program_id=1,
        name="Batch",
        starts_on="2026-11-01",
        ends_on="2027-01-31",
    )
    assert batch.program_id == 1
    with pytest.raises(ValidationError):
        BatchCreate(
            program_id=1,
            batch_code="BAT-2026-0001",
            name="Batch",
            starts_on="2026-11-01",
            ends_on="2027-01-31",
        )

    with pytest.raises(ValidationError):
        EnrollmentCreate(
            student_id=1,
            program_id=1,
            batch_id=1,
            starts_on="2026-11-01",
            agreed_fee_amount="12000.00",
        )
    enrollment = EnrollmentCreate(
        student_id=1,
        batch_id=1,
        starts_on="2026-11-01",
        agreed_fee_amount="12000.00",
    )
    assert enrollment.batch_id == 1

    with pytest.raises(ValidationError):
        ProjectCreate(name="Inventory", project_code="PRJ-2026-0001")
    with pytest.raises(ValidationError):
        CertificateIssueCreate(
            enrollment_id=1,
            certificate_number="CERT-2026-000001",
            certificate_type="Completion",
        )
    with pytest.raises(ValidationError):
        CertificateReplacementCreate(
            certificate_number="CERT-2026-000002",
            reason="Replacement",
        )


def test_program_duration_must_be_positive_months() -> None:
    for duration in (0, -1, 1201):
        with pytest.raises(ValidationError):
            ProgramCreate(name="Python Internship", duration_months=duration)
