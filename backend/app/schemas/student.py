from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.lifecycle import ReasonRequest

StudentStatus = Literal["active", "archived"]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=4000)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=32)
    institution_name: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)
    internship_domain: str | None = Field(default=None, max_length=120)
    program_id: int | None = Field(default=None, gt=0)
    batch_id: int | None = Field(default=None, gt=0)
    agreed_fee_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2
    )
    enrollment_starts_on: date | None = None
    fee_reason: str = Field(default="Initial agreed fee", min_length=1, max_length=500)

    @field_validator(
        "full_name",
        "phone",
        "address",
        "city",
        "state",
        "postal_code",
        "institution_name",
        "course",
        "internship_domain",
        "fee_reason",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_initial_enrollment(self) -> "StudentCreate":
        enrollment_fields = (self.program_id, self.batch_id, self.agreed_fee_amount)
        if any(value is not None for value in enrollment_fields) and any(
            value is None for value in enrollment_fields
        ):
            raise ValueError(
                "Program, batch, and agreed fee must all be supplied to create an enrollment"
            )
        if self.enrollment_starts_on is not None and not all(
            value is not None for value in enrollment_fields
        ):
            raise ValueError("Enrollment start date requires a complete program enrollment")
        if not self.fee_reason.strip():
            raise ValueError("Fee reason cannot be blank")
        return self


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=4000)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=32)
    institution_name: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=200)
    internship_domain: str | None = Field(default=None, max_length=120)
    status: StudentStatus | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator(
        "full_name",
        "phone",
        "address",
        "city",
        "state",
        "postal_code",
        "institution_name",
        "course",
        "internship_domain",
        "reason",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "StudentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one student field must be supplied")
        for field_name in ("full_name", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.status == "archived" and not self.reason:
            raise ValueError("A reason is required when archiving a student")
        return self


class StudentDelete(ReasonRequest):
    pass


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    student_number: str
    full_name: str
    email: EmailStr | None
    phone: str | None
    address: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    institution_name: str | None
    course: str | None
    internship_domain: str | None
    status: StudentStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class StudentPage(BaseModel):
    items: list[StudentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class StudentActivityItem(BaseModel):
    audit_log_id: int
    action: str
    target_type: str | None
    target_id: int | None
    outcome: str
    occurred_at: datetime