from datetime import datetime
from typing import Any, Dict, List, Optional
from app.database import Base
from app.models.waiting_list import WaitingListStatus
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.context_manager import get_db_session
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    ForeignKey,
    func,
    asc,
    desc,
    Boolean
)

class WaitingList(Base):
    __tablename__ = "waiting_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_date_id = Column(Integer, ForeignKey('event_date.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.user_id'), nullable=False)
    number_of_students = Column(Integer, nullable=False)
    number_of_teachers = Column(Integer, nullable=False)
    special_requirements = Column(String(255), nullable=True)
    contact_info = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event_date = relationship("EventDate", back_populates="waiting_list")
    user = relationship("User", back_populates="waiting_list")

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_date_id": self.event_date_id,
            "user_id": self.user_id,
            "number_of_students": self.number_of_students,
            "number_of_teachers": self.number_of_teachers,
            "special_requirements": self.special_requirements,
            "contact_info": self.contact_info,
            "created_at": self.created_at,
        }
    
    @classmethod
    def add_to_waiting_list(cls, waiting_list_entry: Dict[str, Any]) -> Optional['WaitingList']:
        try:
            with get_db_session() as db:
                new_entry = cls(**waiting_list_entry)
                db.add(new_entry)
                db.commit()
                db.refresh(new_entry)
                return new_entry
        except Exception as e:
            print(f"Error adding to waiting list: {str(e)}")
            raise

    @classmethod
    def get_waiting_list_for_event_date(cls, event_date_id: int) -> List['WaitingList']:
        try:
            with get_db_session() as db:
                return db.query(cls).filter(
                    cls.event_date_id == event_date_id,
                    cls.status == WaitingListStatus.WAITING
                ).order_by(cls.created_at).all()
        except Exception as e:
            print(f"Error retrieving waiting list: {str(e)}")
            raise

    @classmethod
    def update_status(cls, entry_id: int, new_status: WaitingListStatus) -> Optional['WaitingList']:
        try:
            with get_db_session() as db:
                entry = db.query(cls).filter(cls.id == entry_id).first()
                if entry:
                    entry.status = new_status
                    db.commit()
                    db.refresh(entry)
                return entry
        except Exception as e:
            print(f"Error updating waiting list entry status: {str(e)}")
            raise