from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from typing import List, Optional, Tuple, Dict, Any, Union


class School(Base):
    __tablename__ = "school"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    ico = Column(String(20), unique=True, nullable=False)  # IČO (Identification number)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with User (school representatives)
    representatives = relationship("User", back_populates="school")

    def __init__(self, name: str, address: str, city: str, ico: str):
        self.name = name
        self.address = address
        self.city = city
        self.ico = ico

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "ico": self.ico,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
