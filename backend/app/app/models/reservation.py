from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    CREATED = "created"


class ReservationCreateModel(BaseModel):
    event_id: int
    user_id: int
    number_of_seats: int
    status: ReservationStatus
    comment: Optional[str] = None


class ReservationUpdateModel(BaseModel):
    number_of_seats: Optional[int] = None
    status: Optional[ReservationStatus] = None
    comment: Optional[str] = None


class ReservationModel(BaseModel):
    id: int
    event_id: int
    user_id: int
    number_of_seats: int
    status: ReservationStatus
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
