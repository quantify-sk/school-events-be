from pydantic import BaseModel, Field
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
    event_date_id: int  # Add this line
    user_id: int
    number_of_students: int
    number_of_teachers: int
    special_requirements: Optional[str] = None
    contact_info: str
    status: ReservationStatus = ReservationStatus.PENDING


class ReservationUpdateModel(BaseModel):
    event_id: Optional[int] = None
    event_date_id: Optional[int] = None  # Add this line
    number_of_students: Optional[int] = None
    number_of_teachers: Optional[int] = None
    special_requirements: Optional[str] = None
    contact_info: Optional[str] = None
    status: Optional[ReservationStatus] = None


class ReservationModel(BaseModel):
    id: int
    event_id: int
    event_date_id: int  # Add this line
    user_id: int
    number_of_students: int
    number_of_teachers: int
    special_requirements: Optional[str] = None
    contact_info: str
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime

    @property
    def total_seats(self) -> int:
        return self.number_of_students + self.number_of_teachers
