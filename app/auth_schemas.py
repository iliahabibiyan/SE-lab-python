from pydantic import BaseModel, ConfigDict, field_validator

from app.validators import normalize_digits


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    national_code: str
    password: str

    @field_validator("national_code", mode="before")
    @classmethod
    def clean_national_code(cls, v):
        return normalize_digits(v) if isinstance(v, str) else v


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int