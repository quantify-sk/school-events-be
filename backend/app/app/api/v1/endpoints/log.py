from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Optional
from app.service.log_service import LogService
from pathlib import Path


router = APIRouter()


log_service = LogService(Path("logs"))

@router.get("/")
async def get_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[int] = None,
    path: Optional[str] = None,
    request_id: Optional[str] = None,
    min_duration: Optional[float] = None,
    current_page: int = 1,  # Added pagination parameters
    items_per_page: int = 10  # Added pagination parameters
):
    logs = log_service.get_logs(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        path=path,
        request_id=request_id,
        min_duration=min_duration,
        current_page=current_page,
        items_per_page=items_per_page
    )
    return {"logs": logs}