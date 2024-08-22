from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator, constr
from app.models.school import SchoolCreateModel, SchoolModel


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    REJECTED = "rejected"


class UserRole(str, Enum):
    ADMIN = "admin"
    ORGANIZER = "organizer"
    SCHOOL_REPRESENTATIVE = "school_representative"
    ANALYST = "analyst"
    USER = "user"
    EMPLOYEE = "employee"


class UserTokenData(BaseModel):
    user_id: int


class UserModel(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    user_email: EmailStr
    status: UserStatus
    password_hash: str
    created_at: datetime
    updated_at: datetime
    role: UserRole
    registration_date: datetime
    email_verified: bool
    preferred_language: str | None = None
    profile_picture: str | None = None
    subscription: str | None = None
    school: SchoolModel | None = None

    def build_user_token_data(self) -> UserTokenData:
        return UserTokenData(
            user_id=self.user_id,
        )


class UserCreateWithoutPasswordModel(BaseModel):
    first_name: str
    last_name: str
    user_email: EmailStr
    role: str = "user"
    email_verified: bool = False
    preferred_language: str | None = None
    profile_picture: str | None = None
    subscription: str | None = None
    school_id: int | None = None
    school: SchoolCreateModel | None = None


class UserCreateModel(UserCreateWithoutPasswordModel):
    password_hash: str

    @field_validator("password_hash")
    def password_validator(cls, password):
        from app.dependencies import get_password_hash

        return get_password_hash(password)


class UserUpdateModel(UserCreateWithoutPasswordModel):
    status: UserStatus | None = None
    role: str | None = None
    email_verified: bool | None = None
    preferred_language: str | None = None
    profile_picture: str | None = None
    subscription: str | None = None
    school: SchoolModel | None = None
