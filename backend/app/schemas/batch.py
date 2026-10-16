from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BatchStatus = Literal["planned", "active", "completed", "cancelled"]


class BatchCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    program_id: int = Field(gt=0)
    batch_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    starts_on: date
    ends_on: date
    capacity: int | None = Field(default=None, gt=0, le=100000)
    status: Literal["planned", "active"] = "planned"

    @field_validator("batch_code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_dates(self) -> "BatchCreate":
        if self.ends_on < self.starts_on:
            raise ValueError("Batch end date must not precede start date")
        return self


class BatchUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    starts_on: date | None = None
    ends_on: date | None = None
    capacity: int | None = Field(default=None, gt=0, le=100000)
    status: BatchStatus | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "BatchUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one editable batch field must be supplied")
        for field_name in ("name", "starts_on", "ends_on", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if (
            self.starts_on is not None
            and self.ends_on is not None
            and self.ends_on < self.starts_on
        ):
            raise ValueError("Batch end date must not precede start date")
        return self


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int
    program_id: int
    batch_code: str
    name: str
    starts_on: date
    ends_on: date
    capacity: int | None
    status: BatchStatus
    created_by: int
    created_at: datetime
    updated_at: datetime


class BatchPage(BaseModel):
    items: list[BatchResponse]
    total: int
    page: int
    page_size: int
    pages: int
