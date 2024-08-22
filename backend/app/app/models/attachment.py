from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AttachmentBase(BaseModel):
    name: str
    type: str
    path: str


class AttachmentCreate(AttachmentBase):
    event_id: int


class AttachmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    path: Optional[str] = None


class AttachmentInDB(AttachmentBase):
    id: int
    event_id: int
    created_at: datetime
    updated_at: datetime


class AttachmentResponse(AttachmentInDB):
    pass


class AttachmentWithData(AttachmentResponse):
    data: str  # Base64 encoded file content
