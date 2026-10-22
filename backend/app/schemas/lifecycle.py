from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReasonRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class DependencySummary(BaseModel):
    resource: str
    identifier: str
    dependencies: dict[str, int]
    can_delete: bool
