from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.event import (
    EventCreateModel,
    EventStatus,
    EventType,
    EventUpdateModel,
    TargetGroup,
)
from app.context_manager import get_db_session
from app.models.get_params import ParameterValidator
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy import func
from app.data_adapter.attachment import Attachment


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)
    description = Column(Text)
    annotation = Column(String(500))
    target_group = Column(SAEnum(TargetGroup), nullable=False)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.SCHEDULED)
    event_type = Column(SAEnum(EventType), nullable=False)
    duration = Column(Float, nullable=False)
    parent_info = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organizer_id = Column(Integer, ForeignKey("user.user_id"))

    # Relationships
    attachments = relationship(
        "Attachment", back_populates="event", cascade="all, delete-orphan"
    )
    organizer = relationship("User", back_populates="organized_events")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attachments = []  # Initialize attachments as an empty list
        for k, v in kwargs.items():
            if k == "attachments" and v is not None:
                self.attachments = v
            else:
                setattr(self, k, v)
        self.available_spots = self.capacity

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "address": self.address,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity": self.capacity,
            "available_spots": self.available_spots,
            "description": self.description,
            "annotation": self.annotation,
            "target_group": self.target_group,
            "status": self.status,
            "event_type": self.event_type,
            "duration": self.duration,
            "parent_info": self.parent_info,
            "attachments": [attachment._to_model() for attachment in self.attachments],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organizer_id": self.organizer_id,
        }

    def book_seats(self, number_of_seats: int) -> bool:
        if self.available_spots >= number_of_seats:
            self.available_spots -= number_of_seats
            return True
        return False

    @classmethod
    def create_new_event(
        cls, event_data: EventCreateModel, attachments: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        db = get_db_session()
        new_event = cls(**event_data.dict(exclude={"attachments"}))
        new_event.available_spots = new_event.capacity

        if attachments:
            for attachment_data in attachments:
                attachment = Attachment(**attachment_data, event=new_event)
                db.add(attachment)

        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        return new_event._to_model()

    @classmethod
    def update_event_by_id(
        cls,
        event_id: int,
        event_data: EventUpdateModel,
        existing_attachment_ids: List[int],
        new_attachments: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        db = get_db_session()
        event = db.query(cls).filter(cls.id == event_id).first()
        if event:
            update_data = event_data.dict(exclude_unset=True)

            # Handle attachments
            existing_attachments = (
                db.query(Attachment).filter(Attachment.event_id == event_id).all()
            )

            # Remove attachments not in existing_attachment_ids
            for attachment in existing_attachments:
                if attachment.id not in existing_attachment_ids:
                    db.delete(attachment)

            # Add new attachments
            for attachment_data in new_attachments:
                new_attachment = Attachment(**attachment_data, event_id=event_id)
                db.add(new_attachment)

            # Update other fields
            for field, value in update_data.items():
                if field != "attachments":
                    setattr(event, field, value)

            if "capacity" in update_data:
                spots_taken = event.capacity - event.available_spots
                event.available_spots = max(0, update_data["capacity"] - spots_taken)

            db.commit()
            db.refresh(event)
            return event._to_model()
        return None

    @classmethod
    def delete_event_by_id(cls, event_id: int) -> bool:
        db = get_db_session()
        event = db.query(cls).filter(cls.id == event_id).first()
        if event:
            db.delete(event)
            db.commit()
            return True
        return False

    @classmethod
    def get_event_by_id(cls, event_id: int) -> Optional[Dict[str, Any]]:
        db = get_db_session()
        event = db.query(cls).filter(cls.id == event_id).first()
        return event._to_model() if event else None

    @classmethod
    def get_events(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        coordinates: Optional[str] = None,
        radius: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_db_session()
        query = db.query(cls)

        # Apply date range filter
        if date_from:
            query = query.filter(cls.date >= date_from)
        if date_to:
            query = query.filter(cls.date <= date_to)

        # Apply location-based filter
        if coordinates and radius:
            lat, lon = map(float, coordinates.split(","))
            distance = func.sqrt(
                func.pow(69.1 * (cls.latitude - lat), 2)
                + func.pow(
                    69.1 * (lon - cls.longitude) * func.cos(cls.latitude / 57.3), 2
                )
            )
            query = query.filter(distance <= radius)

        # Apply additional filters and sorting
        query = ParameterValidator.apply_filters_and_sorting(
            query,
            cls,
            filter_params,
            sorting_params,
        )

        # Get total count and paginate results
        total_count = query.count()
        events = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [event._to_model() for event in events], total_count

    @classmethod
    def get_organizer_events(
        cls,
        organizer_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        coordinates: Optional[str] = None,
        radius: Optional[float] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_db_session()
        query = db.query(cls).filter(cls.organizer_id == organizer_id)

        query = ParameterValidator.apply_filters_and_sorting(
            query,
            cls,
            filter_params,
            sorting_params,
        )

        if date_from:
            query = query.filter(cls.date >= date_from)
        if date_to:
            query = query.filter(cls.date <= date_to)

        if coordinates and radius:
            lat, lon = map(float, coordinates.split(","))
            distance = func.sqrt(
                func.pow(69.1 * (cls.latitude - lat), 2)
                + func.pow(
                    69.1 * (lon - cls.longitude) * func.cos(cls.latitude / 57.3), 2
                )
            )
            query = query.filter(distance <= radius)

        total_count = query.count()
        events = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [event._to_model() for event in events], total_count
