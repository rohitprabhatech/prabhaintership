from pydantic import BaseModel


class FieldIssue(BaseModel):
    location: list[str | int]
    message: str
    code: str


class ErrorResponse(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    request_id: str
    errors: list[FieldIssue] | None = None