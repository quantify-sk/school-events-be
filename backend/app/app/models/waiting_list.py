from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class WaitingListStatus(str, Enum):
    WAITING = "waiting"
    PROCESSED = "processed"
    CANCELLED = "cancelled"

class WaitingListCreateModel(BaseModel):
    event_id: int
    event_date_id: int
    user_id: int
    number_of_students: int
    number_of_teachers: int
    special_requirements: Optional[str] = None
    contact_info: str
    status: WaitingListStatus = WaitingListStatus.WAITING

class WaitingListUpdateModel(BaseModel):
    number_of_students: Optional[int] = None
    number_of_teachers: Optional[int] = None
    special_requirements: Optional[str] = None
    contact_info: Optional[str] = None
    status: Optional[WaitingListStatus] = None

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
    updated_at: datetime

    @property
    def total_seats(self) -> int:
        return self.number_of_students + self.number_of_teachers
    
# And create a model for setting the lock time
class SetLockTimeModel(BaseModel):
    event_date_id: int
    hours_before: int = Field(default=24, ge=0)