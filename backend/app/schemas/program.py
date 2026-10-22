from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.lifecycle import ReasonRequest

ProgramStatus = Literal["draft", "active", "inactive"]


class ProgramCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    duration_months: int = Field(gt=0, le=1200)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "active"] = "draft"

    @field_validator("name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProgramUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    duration_months: int | None = Field(default=None, gt=0, le=1200)
    description: str | None = Field(default=None, max_length=4000)
    status: ProgramStatus | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("name", "reason", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "ProgramUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one editable program field must be supplied")
        for field_name in ("name", "duration_months"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"Program {field_name} cannot be null")
        if self.status == "inactive" and not self.reason:
            raise ValueError("A reason is required when deactivating a program")
        return self


class ProgramDelete(ReasonRequest):
    pass


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_id: int
    program_code: str
    name: str
    duration_months: int | None
    description: str | None
    status: ProgramStatus
    created_by: int
    created_at: datetime
    updated_at: datetime


class ProgramPage(BaseModel):
    items: list[ProgramResponse]
    total: int
    page: int
    page_size: int
    pages: int
