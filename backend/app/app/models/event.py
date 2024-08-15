import base64
import json
import os
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    DateTime,
    JSON,
    Text,
    Enum as SAEnum,
)
from datetime import datetime
from app.database import Base
from app.context_manager import get_db_session
from app.models.get_params import ParameterValidator
from typing import List, Dict, Optional, Tuple, Union, Any
from sqlalchemy import func
from enum import Enum
from pydantic import BaseModel


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
    OTHER = "other"


class TargetGroup(str, Enum):
    ELEMENTARY_SCHOOL = "elementary_school"
    HIGH_SCHOOL = "high_school"
    ALL = "all"


class AttachmentModel(BaseModel):
    name: str
    url: str


class EventCreateModel(BaseModel):
    title: str
    date: datetime
    time: datetime
    address: str
    city: str
    latitude: float
    longitude: float
    capacity: int
    description: Optional[str] = None
    annotation: Optional[str] = None
    target_group: TargetGroup
    event_type: EventType
    duration: float
    parent_info: Optional[str] = None
    organizer_id: int

class EventUpdateModel(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime] = None
    time: Optional[datetime] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
    annotation: Optional[str] = None
    target_group: Optional[TargetGroup] = None
    status: Optional[EventStatus] = None
    event_type: Optional[EventType] = None
    duration: Optional[float] = None
    parent_info: Optional[str] = None
    organizer_id: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class EventModel(BaseModel):
    id: int
    title: str
    date: datetime
    time: datetime
    address: str
    city: str
    latitude: float
    longitude: float
    capacity: int
    available_spots: int
    description: Optional[str] = None
    annotation: Optional[str] = None
    target_group: TargetGroup
    status: EventStatus
    event_type: EventType
    duration: float
    parent_info: Optional[str] = None
    attachments: List[AttachmentModel]
    created_at: datetime
    updated_at: datetime
    organizer_id: int 
