from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class FeeTermCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    agreed_amount: Money
    reason: str = Field(min_length=1, max_length=500)


class FeeTermResponse(BaseModel):
    fee_term_id: int
    enrollment_id: int
    fee_structure_id: int | None
    agreed_amount: Decimal
    currency: str
    effective_from: datetime
    effective_to: datetime | None
    reason: str
    created_by: int
    created_at: datetime


class FeeAdjustmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    adjustment_type: Literal["discount", "fee_increase"]
    amount: Money
    reason: str = Field(min_length=1, max_length=500)


class FeeAdjustmentResponse(BaseModel):
    fee_adjustment_id: int
    enrollment_id: int
    adjustment_type: Literal["discount", "fee_increase"]
    amount: Decimal
    reason: str
    approved_by: int
    approved_at: datetime


class FeeSummary(BaseModel):
    enrollment_id: int
    enrollment_number: str
    fee_term_id: int
    base_fee: Decimal
    adjustments_total: Decimal
    effective_fee: Decimal
    currency: Literal["INR"]
    net_paid: Decimal
    pending_balance: Decimal


class PaymentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    amount: Money
    payment_method: Literal["cash", "bank_transfer", "upi", "card", "cheque", "other"]
    payment_reference: str | None = Field(default=None, max_length=256)
    paid_at: datetime | None = None

    @field_validator("payment_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value


class PaymentResponse(BaseModel):
    payment_id: int
    enrollment_id: int
    amount: Decimal
    currency: Literal["INR"]
    paid_at: datetime
    payment_method: str
    payment_reference: str | None
    recorded_by: int
    created_at: datetime
    adjusted_amount: Decimal
    net_amount: Decimal
    derived_status: Literal["posted", "partially_refunded", "refunded", "reversed"]


class PaymentPage(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaymentAdjustmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    adjustment_type: Literal["refund", "reversal"]
    amount: Money
    reason: str = Field(min_length=1, max_length=500)


class PaymentAdjustmentResponse(BaseModel):
    adjustment_id: int
    payment_id: int
    adjustment_type: Literal["refund", "reversal"]
    amount: Decimal
    occurred_at: datetime
    reason: str
    recorded_by: int


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    project_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("project_code")
    @classmethod
    def normalize_project_code(cls, value: str) -> str:
        return value.upper()


class ProjectResponse(BaseModel):
    project_id: int
    project_code: str
    name: str
    description: str | None
    status: Literal["active", "archived"]
    created_by: int
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int = Field(gt=0)


class ProjectAssignmentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["in_progress", "completed", "cancelled"]


class ProjectAssignmentResponse(BaseModel):
    project_assignment_id: int
    project_id: int
    enrollment_id: int
    status: Literal["assigned", "in_progress", "completed", "cancelled"]
    assigned_at: datetime
    completed_at: datetime | None
    assigned_by: int
    created_at: datetime
    updated_at: datetime
    project_code: str | None = None
    project_name: str | None = None


class ProjectAssignmentPage(BaseModel):
    items: list[ProjectAssignmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CertificateIssueCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    enrollment_id: int = Field(gt=0)
    certificate_number: str = Field(min_length=1, max_length=128)
    certificate_type: str = Field(min_length=1, max_length=128)
    issued_at: datetime | None = None
    document_uri: str | None = Field(default=None, max_length=2048)


class CertificateReplacementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    certificate_number: str = Field(min_length=1, max_length=128)
    issued_at: datetime | None = None
    document_uri: str | None = Field(default=None, max_length=2048)
    reason: str = Field(min_length=1, max_length=500)


class CertificateEventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class CertificateResponse(BaseModel):
    certificate_id: int
    enrollment_id: int
    certificate_number: str
    certificate_type: str
    issued_at: datetime
    document_uri: str | None
    replaces_certificate_id: int | None
    issued_by: int
    created_at: datetime
    derived_status: Literal["issued", "replaced", "revoked"]
    terminal_event_at: datetime | None
    enrollment_number: str | None = None
    student_number: str | None = None
    full_name: str | None = None
    program_code: str | None = None


class CertificateEventResponse(BaseModel):
    certificate_event_id: int
    certificate_id: int
    event_type: Literal["replaced", "revoked", "corrected"]
    related_certificate_id: int | None
    occurred_at: datetime
    reason: str
    recorded_by: int


class CertificateReportPage(BaseModel):
    items: list[CertificateResponse]
    total: int
    page: int
    page_size: int
    pages: int
