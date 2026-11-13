from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    #: Phase 30：唯讀 viewer（計算值，預設 False；由 visibility_service 附帶）
    is_read_only: bool = False


class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)

    model_config = ConfigDict(extra="forbid")


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class PasswordChangeResponse(BaseModel):
    """Phase 44：改密碼會撤銷所有 session，回應重新簽發目前裝置的 access token
    （refresh cookie 同時重設）。`success` 為既有欄位，保留相容。"""

    success: bool = True
    access_token: str
    token_type: str = "bearer"


class UserAdminUpdate(BaseModel):
    is_active: bool

    model_config = ConfigDict(extra="forbid")
