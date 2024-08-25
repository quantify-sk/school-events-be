from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, time, date
from enum import Enum


class EventStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    PUBLIC = "public"


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