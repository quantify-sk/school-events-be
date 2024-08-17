from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator, constr


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


class SchoolRepresentativeCreateModel(BaseModel):
    first_name: str
    last_name: str
    user_email: EmailStr
    password: str
    phone_number: str
    school_name: str
    school_address: str
    school_ico: constr(min_length=8, max_length=8)  # IČO is typically 8 digits
    additional_info: str | None = None

    @field_validator("password")
    def password_validator(cls, password):
        # You can add more complex password validation here
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return password

    @field_validator("phone_number")
    def phone_number_validator(cls, phone_number):
        # Add phone number validation if needed
        # This is a simple example; you might want to use a more robust validation
        if not phone_number.isdigit() or len(phone_number) < 9:
            raise ValueError("Invalid phone number format")
        return phone_number

    @field_validator("school_ico")
    def school_ico_validator(cls, school_ico):
        if not school_ico.isdigit():
            raise ValueError("IČO must contain only digits")
        return school_ico


class SchoolRepresentativeResponseModel(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    user_email: EmailStr
    phone_number: str
    school_name: str
    school_address: str
    school_ico: str
    status: UserStatus
    role: UserRole = UserRole.SCHOOL_REPRESENTATIVE
    created_at: datetime
    updated_at: datetime


class SchoolRepresentativeApprovalModel(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    user_email: EmailStr
    school_name: str
    school_ico: str
    created_at: datetime
