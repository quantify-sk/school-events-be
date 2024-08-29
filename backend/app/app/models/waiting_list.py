from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class WaitingListStatus(str, Enum):
    WAITING = "waiting"
    PROCESSED = "processed"
    CANCELLED = "cancelled"


class WaitingListCreateModel(BaseModel):
    event_date_id: int
    user_id: int
    number_of_students: int
    number_of_teachers: int
    special_requirements: Optional[str] = None
    contact_info: str
    # Position will be automatically assigned in the service layer


class WaitingListUpdateModel(BaseModel):
    number_of_students: Optional[int] = None
    number_of_teachers: Optional[int] = None
    special_requirements: Optional[str] = None
    contact_info: Optional[str] = None
    status: Optional[WaitingListStatus] = None
    # Position should not be directly updatable by users


class WaitingListModel(BaseModel):
    id: int
    event_id: int
    event_date_id: int
    user_id: int
    number_of_students: int
    number_of_teachers: int
    special_requirements: Optional[str] = None
    contact_info: str
    status: WaitingListStatus
    created_at: datetime
    position: int  # Add position field

    @property
    def total_seats(self) -> int:
        return self.number_of_students + self.number_of_teachers


class SetLockTimeModel(BaseModel):
    event_date_id: int
    hours_before: int = Field(default=48, ge=0)
