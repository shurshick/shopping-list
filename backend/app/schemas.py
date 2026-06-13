from datetime import datetime

from pydantic import ConfigDict
from pydantic import BaseModel, EmailStr, Field


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PublicServerConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    app_name: str
    external_url: str
    allow_registration: bool
    setup_completed: bool


class ListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    client_operation_id: str | None = Field(default=None, max_length=64)
    temp_id: str | None = Field(default=None, max_length=64)


class ListUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    quantity: str = Field(default="", max_length=80)
    is_checked: bool = False
    client_operation_id: str | None = Field(default=None, max_length=64)
    temp_id: str | None = Field(default=None, max_length=64)


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    quantity: str | None = Field(default=None, max_length=80)
    is_checked: bool | None = None


class ShareRequest(BaseModel):
    email: EmailStr


class ListMemberResponse(BaseModel):
    id: int
    email: EmailStr
    is_owner: bool


class MembersResponse(BaseModel):
    members: list[ListMemberResponse]


class ActivityLogResponse(BaseModel):
    id: int
    list_id: int | None
    user_id: int | None
    user_email: EmailStr | None = None
    action: str
    item_id: int | None
    item_name: str
    details: str
    created_at: datetime


class ActivityResponse(BaseModel):
    events: list[ActivityLogResponse]


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    migration: str | None
    server_time: datetime


class AdminStatusResponse(BaseModel):
    version: str
    database: str
    migration: str | None
    server_time: datetime
    users_count: int
    lists_count: int
    items_count: int
    checked_items_count: int
    activity_events_count: int
    invites_active_count: int
    pending_invites_count: int
    invite_token_hours: int
    app_name: str
    external_url: str
    allow_registration: bool
    setup_completed: bool


class InviteResponse(BaseModel):
    token: str
    url: str
    app_url: str
    expires_at: datetime | None = None


class SyncItem(BaseModel):
    id: int
    name: str
    quantity: str
    is_checked: bool
    updated_at: datetime


class SyncList(BaseModel):
    id: int
    name: str
    owner_id: int
    updated_at: datetime
    items: list[SyncItem]


class SyncResponse(BaseModel):
    lists: list[SyncList]
