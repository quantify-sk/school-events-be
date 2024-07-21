from datetime import date
from enum import Enum

from pydantic import BaseModel


class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    DELETED = "deleted"


class NotificationModel(BaseModel):
    notification_id: int
    notification_content: str
    notification_date: date
    notification_type: NotificationType
    notification_status: NotificationStatus
    send_notification: bool


class NotificationCreateModel(BaseModel):
    notification_content: str
    notification_date: date
    notification_type: NotificationType
