from datetime import date, datetime
from decimal import Decimal
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.lifecycle import ReasonRequest

EnrollmentStatus = Literal["active", "completed", "withdrawn", "cancelled"]


class EnrollmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_id: int = Field(gt=0)
    batch_id: int = Field(gt=0)
    starts_on: date
    ends_on: date | None = None
    agreed_fee_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    fee_reason: str = Field(default="Initial agreed fee", min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self) -> "EnrollmentCreate":
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("Enrollment end date must not precede start date")
        return self


class EnrollmentStatusUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: EnrollmentStatus
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_cancel_reason(self) -> "EnrollmentStatusUpdate":
        if self.status in {"cancelled", "withdrawn"} and not self.reason:
            raise ValueError("A reason is required when cancelling or withdrawing an enrollment")
        return self


class EnrollmentDelete(ReasonRequest):
    pass


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enrollment_id: int
    enrollment_number: str
    student_id: int
    program_id: int
    batch_id: int
    status: EnrollmentStatus
    starts_on: date
    ends_on: date | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class EnrollmentPage(BaseModel):
    items: list[EnrollmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BatchRosterStudent(BaseModel):
    enrollment_id: int
    enrollment_number: str
    enrollment_status: EnrollmentStatus
    enrollment_starts_on: date
    enrollment_ends_on: date | None
    student_id: int
    student_number: str
    full_name: str
    email: str | None
    phone: str | None


class BatchRoster(BaseModel):
    batch_id: int
    program_id: int
    batch_code: str
    name: str
    starts_on: date
    ends_on: date
    capacity: int | None
    active_enrollment_count: int
    students: list[BatchRosterStudent]


class BatchFeeSummary(BaseModel):
    effective_fee: Decimal
    net_paid: Decimal
    pending_balance: Decimal
    currency: Literal["INR"]


class BatchStudentRow(BatchRosterStudent):
    fee_summary: BatchFeeSummary | None


class BatchRosterPage(BaseModel):
    batch_id: int
    program_id: int
    batch_code: str
    name: str
    starts_on: date
    ends_on: date
    capacity: int | None
    enrollment_count: int
    active_enrollment_count: int
    unique_active_student_count: int
    students: list[BatchStudentRow]
    total: int
    page: int
    page_size: int
    pages: int
