from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date


class StatisticsRequestModel(BaseModel):
    start_date: Optional[date] = None  # Filter by start date
    end_date: Optional[date] = None  # Filter by end date
    event_type: Optional[str] = None  # Filter by event type (Druh podujatia)
    venue: Optional[str] = None  # Filter by venue (Muzea, divadla, etc.)
    organizer_id: Optional[str] = None  # Filter by organizer
    district: Optional[str] = None  # Filter by district (Okres)
    region: Optional[str] = None  # Filter by region (Kraj)
    target_group: Optional[str] = None  # Filter by target group (Cielova skupina)


class ChartData(BaseModel):
    labels: List[str]
    data: List[Any]


class StatisticsResponseModel(BaseModel):
    summary: Dict[str, Any]
    details: Dict[str, Any]
    charts: Dict[str, ChartData]
