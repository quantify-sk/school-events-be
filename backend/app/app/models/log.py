from datetime import datetime
from typing import Dict, Optional

from app.models.user import UserModel
from pydantic import BaseModel


class LogModel(BaseModel):
    log_id: int
    timestamp: datetime
    table_name: str
    user_id: Optional[int]
    table_primary_key: int
    old_data: Optional[Dict]
    new_data: Optional[Dict]

    # Relationships
    user: Optional["UserModel"]
