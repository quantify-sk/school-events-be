from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr


class EmailLogLanguage(str, Enum):
    """Enum for Email log language"""

    EN = "en"
    SK = "sk"
    CZ = "cz"


class EmailLogStatus(str, Enum):
    """Enum for Email log status"""

    PENDING = "Pending"
    SUCCESS = "Success"
    FAILED = "Failed"


class EmailLogTemplates(str, Enum):
    """Enum for Email log templates"""

    USER_REGISTRATION = "user_registration.html"
    USER_REGISTRATION_ADMIN_NOTIFICATION = "user_registration_admin_notification.html"
    USER_REGISTRATION_INFO = "user_registration_info.html"
    SCHOOL_REPRESENTATIVE_RESERVATION = "school_representative_reservation.html"
    EVENT_DATA_CHANGE = "event_date_data_change.html"
    USER_RESET_PASSWORD = "user_reset_password.html"
    SCHOOL_REPRESENTATIVE_DATE_INCOMING = "school_representative_date_incoming.html"
    USER_ACCOUNT_ACTIVATION = "user_account_activation.html"
    USER_ACCOUNT_REJECTION = "user_account_rejection.html"
    ORGANIZER_CLAIM_ACCEPTED = "organizer_claim_accepted.html"
    ORGANIZER_CLAIM_REJECTED = "organizer_claim_rejected.html"


class EmailLogTypes(str, Enum):
    """Enum for Email log types"""

    USER_REGISTRATION = "user_registration"
    USER_REGISTRATION_INFO = "user_registration_info"
    EVENT_DATA_CHANGE = "event_date_data_change"
    USER_RESET_PASSWORD = "user_reset_password"
    USER_ACCOUNT_ACTIVATION = "user_account_activation"
    USER_ACCOUNT_REJECTION = "user_account_rejection"
    ORGANIZER_CLAIM_ACCEPTED = "organizer_claim_accepted"
    ORGANIZER_CLAIM_REJECTED = "organizer_claim_rejected"
    SCHOOL_REPRESENTATIVE_RESERVATION = "school_representative_reservation"
    SCHOOL_REPRESENTATIVE_DATE_INCOMING = "school_representative_date_incoming"
    USER_REGISTRATION_ADMIN_NOTIFICATION = "user_registration_admin_notification"


class EmailLogModel(BaseModel):
    """Email Log model"""

    email_log_id: int
    user_id: int
    recipient_email: EmailStr
    subject: str
    email_data: str
    email_template: EmailLogTemplates
    status: EmailLogStatus
    language: EmailLogLanguage
    email_type: EmailLogTypes
    retry_count: int
    response: str | None
    priority: int
    created_at: datetime
    updated_at: datetime


class EmailLogCreateModel(BaseModel):
    """Email Log creation model"""

    recipient_email: EmailStr
    subject: str
    email_data: str
    email_template: EmailLogTemplates
    email_type: EmailLogTypes
    language: EmailLogLanguage
    priority: int = 100


class EmailLogUpdateModel(BaseModel):
    """Email Log update model"""

    status: EmailLogStatus
    retry_count: int


class EmailLogInfoModel(BaseModel):
    """Email Log info model"""

    recipient_email: EmailStr
    subject: str
    email_data: str
    email_template: EmailLogTemplates