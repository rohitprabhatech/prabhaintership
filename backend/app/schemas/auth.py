from pydantic import BaseModel, ConfigDict, Field, SecretStr


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    new_password: SecretStr = Field(min_length=1, max_length=1024)
    confirm_password: SecretStr = Field(min_length=1, max_length=1024)


class ChangePasswordResponse(BaseModel):
    message: str
    reauthenticate: bool


class AdminPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    admin_id: int
    username: str
    email: str | None
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminPublic