from uuid import UUID

from pydantic import BaseModel, EmailStr, field_serializer


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "agent"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str | UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    api_key_prefix: str | None = None

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v)


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
