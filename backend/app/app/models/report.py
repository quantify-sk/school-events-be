from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class ReportType(str, Enum):
    EVENT_SUMMARY = "event_summary"
    ATTENDANCE = "attendance"
    FEEDBACK = "feedback"
    RESERVATION = "reservation"

class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class ReportFilters(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[int] = None
    report_type: ReportType
    event_type: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    reservation_status: Optional[ReservationStatus] = None

class ReportBaseModel(BaseModel):
    report_type: ReportType
    generated_on: datetime
    generated_by: int
    filters: Optional[ReportFilters]
    data: Optional[List[Dict[str, Any]]]

class ReportCreateModel(ReportBaseModel):
    pass

class ReportModel(ReportBaseModel):
    id: int

class ReportResponse(BaseModel):
    api_id: str
    message: str
    status_code: int
    data: ReportModel