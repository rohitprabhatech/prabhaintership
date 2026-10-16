from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

StudentStatus = Literal["active", "archived"]


class StudentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_number: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)

    @field_validator("student_number", "full_name", "phone", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_number: str | None = Field(default=None, min_length=1, max_length=64)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    status: StudentStatus | None = None

    @field_validator("student_number", "full_name", "phone", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch(self) -> "StudentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one student field must be supplied")
        for field_name in ("student_number", "full_name", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    student_number: str
    full_name: str
    email: EmailStr | None
    phone: str | None
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