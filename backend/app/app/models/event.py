from pydantic import BaseModel, Field
import threading
from typing import List, Optional
from datetime import datetime, time, date
from enum import Enum


class EventStatus(str, Enum):
    PUBLISHED = "published"
    SENT_PAYMENT = "completed_payment_sent"
    CANCELLED = "cancelled"
    COMPLETED = "completed_paid"
    COMPLETED_UNPAID = "completed_unpaid"
    


class EventType(str, Enum):
    THEATER = "theater"
    CONCERT = "concert"
    EXHIBITION = "exhibition"
    WORKSHOP = "workshop"
    SCREENING = "screening"
    PERFORMANCE = "performance"
    DANCE = "dance"
    OPERA = "opera"
    BALLET = "ballet"
    OTHER = "other"

class ClaimType(str, Enum):
    CANCEL_DATE = "cancel_date"
    DELETE_EVENT = "delete_event"

class ClaimStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TargetGroup(str, Enum):
    ELEMENTARY_SCHOOL = "elementary_school"
    HIGH_SCHOOL = "high_school"
    ALL = "all"


class AttachmentModel(BaseModel):
    id: Optional[int] = None
    name: str
    path: str
    type: str


class EventDateModel(BaseModel):
    id: int
    event_id: int
    date: date
    time: time
    capacity: int
    available_spots: int
    lock_time: Optional[datetime] = None
    is_locked: bool = False
    status: EventStatus = EventStatus.PUBLISHED

    class Config:
        from_attributes = True


class EventCreateModel(BaseModel):
    title: str
    institution_name: str
    address: str
    city: str
    capacity: int
    description: Optional[str] = None
    annotation: Optional[str] = None
    parent_info: Optional[str] = None  # Added parent info
    target_group: TargetGroup
    age_from: int = Field(..., ge=0)
    age_to: Optional[int] = Field(None, ge=0)
    event_type: EventType
    duration: int  # Duration in minutes
    organizer_id: int
    more_info_url: Optional[str] = None  # Added more info URL
    attachments: Optional[List[AttachmentModel]] = None
    event_dates: List[EventDateModel]
    parking_spaces: Optional[int] = None  # Added parking spaces
    ztp_access: Optional[bool] = None  # Added ZTP access
    region: Optional[str] = None  # Added region
    district: Optional[str] = None  # Added district


class EventUpdateModel(BaseModel):
    title: Optional[str] = None
    institution_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None  # Added district
    region: Optional[str] = None  # Added region
    capacity: Optional[int] = None
    description: Optional[str] = None
    annotation: Optional[str] = None
    parent_info: Optional[str] = None  # Added parent info
    target_group: Optional[TargetGroup] = None
    age_from: Optional[int] = Field(None, ge=0)
    age_to: Optional[int] = Field(None, ge=0)
    status: Optional[EventStatus] = None
    event_type: Optional[EventType] = None
    duration: Optional[int] = None  # Duration in minutes
    organizer_id: Optional[int] = None
    more_info_url: Optional[str] = None  # Added more info URL
    attachments: Optional[List[AttachmentModel]] = None
    event_dates: Optional[List[EventDateModel]] = None
    ztp_access: Optional[bool] = None  # Added ZTP access
    parking_spaces: Optional[int] = None  # Added parking spaces
    


class EventModel(BaseModel):
    id: int
    title: str
    institution_name: str
    address: str
    city: str
    district: str  # Added district
    region: str  # Added region
    capacity: int
    available_spots: int
    description: Optional[str] = None
    annotation: Optional[str] = None
    parent_info: Optional[str] = None  # Added parent info
    target_group: TargetGroup
    age_from: int
    age_to: Optional[int]
    status: EventStatus
    event_type: EventType
    duration: int  # Duration in minutes
    more_info_url: Optional[str] = None  # Added more info URL
    attachments: List[AttachmentModel]
    event_dates: List[EventDateModel]
    created_at: datetime
    updated_at: datetime
    organizer_id: int
    claims: Optional[List["EventClaimModel"]] = None


class EventFilterParams(BaseModel):
    title: Optional[str] = None
    institution_name: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None  # Added district
    region: Optional[str] = None  # Added region
    target_group: Optional[TargetGroup] = None
    age: Optional[int] = None
    event_type: Optional[EventType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    organizer_id: Optional[int] = None


class EventSortParams(BaseModel):
    field: str
    order: str = "asc"

class EventClaimCreateModel(BaseModel):
    """
    Pydantic model for creating a new event claim.
    """
    event_id: int
    event_date_ids: Optional[List[int]] = None
    organizer_id: int
    claim_type: ClaimType
    reason: str

class EventClaimModel(BaseModel):
    """
    Pydantic model for representing an event claim.
    """
    id: int
    event_id: int
    event_date_id: Optional[int]
    organizer_id: int
    claim_type: ClaimType
    reason: str
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime