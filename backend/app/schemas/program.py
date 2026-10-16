from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProgramStatus = Literal["draft", "active", "inactive"]


class ProgramCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    program_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "active"] = "draft"

    @field_validator("program_code", "name", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class ProgramUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: ProgramStatus | None = None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "ProgramUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one editable program field must be supplied")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Program name cannot be null")
        return self


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_id: int
    program_code: str
    name: str
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
