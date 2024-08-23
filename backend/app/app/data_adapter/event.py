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
from sqlalchemy.orm import relationship, joinedload
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
from app.data_adapter.attachment import Attachment


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    institution_name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)
    description = Column(Text)
    annotation = Column(Text)
    parent_info = Column(Text, nullable=True)  # Changed to nullable
    target_group = Column(SAEnum(TargetGroup), nullable=False)
    age_from = Column(Integer, nullable=False)
    age_to = Column(Integer, nullable=True)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.SCHEDULED)
    event_type = Column(SAEnum(EventType), nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in minutes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organizer_id = Column(Integer, ForeignKey("user.user_id"))
    more_info_url = Column(String(255), nullable=True)  # New field for additional information URL
    ztp_access = Column(Boolean, default=False, nullable=False)
    parking_spaces = Column(Integer, default=0, nullable=False)

    # Relationships remain the same
    attachments = relationship(
        "Attachment", back_populates="event", cascade="all, delete-orphan"
    )
    organizer = relationship("User", back_populates="organized_events")
    event_dates = relationship(
        "EventDate", back_populates="event", cascade="all, delete-orphan"
    )
    reservations = relationship("Reservation", back_populates="event")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attachments = []
        self.event_dates = []
        for k, v in kwargs.items():
            if k == "attachments" and v is not None:
                self.attachments = v
            elif k == "event_dates" and v is not None:
                self.event_dates = v
            else:
                setattr(self, k, v)
        self.available_spots = self.capacity

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "institution_name": self.institution_name,
            "address": self.address,
            "city": self.city,
            "capacity": self.capacity,
            "available_spots": self.available_spots,
            "description": self.description,
            "annotation": self.annotation,
            "parent_info": self.parent_info,
            "target_group": self.target_group,
            "age_from": self.age_from,
            "age_to": self.age_to,
            "status": self.status,
            "event_type": self.event_type,
            "duration": self.duration,
            "more_info_url": self.more_info_url,
            "attachments": [attachment._to_model() for attachment in self.attachments],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organizer_id": self.organizer_id,
            "ztp_access": self.ztp_access,
            "parking_spaces": self.parking_spaces,
            "event_dates": [event_date._to_model() for event_date in self.event_dates],
        }

    @classmethod
    def create_new_event(
        cls, event_data: EventCreateModel, attachments: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        db = get_db_session()
        new_event = cls(**event_data.dict(exclude={"attachments", "event_dates"}))
        new_event.available_spots = new_event.capacity

        if attachments:
            for attachment_data in attachments:
                attachment = Attachment(**attachment_data, event=new_event)
                db.add(attachment)

        for event_date in event_data.event_dates:
            new_event_date = EventDate(**event_date.dict(), event=new_event)
            db.add(new_event_date)

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

            # Update event dates
            if "event_dates" in update_data:
                db.query(EventDate).filter(EventDate.event_id == event_id).delete()
                for event_date in update_data["event_dates"]:
                    # Combine date and time into a single DateTime object
                    combined_datetime = datetime.combine(event_date['date'], event_date['time'])
                    new_event_date = EventDate(
                        event_id=event_id,
                        date=combined_datetime,
                        time=combined_datetime
                    )
                    db.add(new_event_date)

            # Update other fields
            for field, value in update_data.items():
                if field not in ["attachments", "event_dates"]:
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
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve events with pagination, filtering, and sorting.
    
        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.
    
        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing the list of events and the total count.
        """
        db = get_db_session()
    
        # Start with a subquery to get the earliest date for each event
        date_subquery = (
            db.query(EventDate.event_id, func.min(EventDate.date).label('min_date'))
            .group_by(EventDate.event_id)
            .subquery()
        )
    
        # Main query
        query = db.query(cls).join(date_subquery, cls.id == date_subquery.c.event_id)
    
        # Apply date range filter if provided
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params.pop("event_dates")
            if "date_from" in date_filters:
                query = query.filter(date_subquery.c.min_date >= date_filters["date_from"])
            if "date_to" in date_filters:
                query = query.filter(date_subquery.c.min_date <= date_filters["date_to"])
    
        # Apply additional filters using ParameterValidator
        if filter_params:
            query = ParameterValidator.apply_filters_and_sorting(
                query,
                cls,
                filter_params,
                None,  # We'll handle sorting separately
            )
    
        # Apply sorting
        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(
                            date_subquery.c.min_date.asc() if value == "asc" else date_subquery.c.min_date.desc()
                        )
                    else:
                        column = getattr(cls, key)
                        query = query.order_by(column.asc() if value == "asc" else column.desc())
        else:
            # Default sorting by earliest date
            query = query.order_by(date_subquery.c.min_date.asc())
    
        # Get total count of distinct events
        total_count = query.count()
    
        # Apply pagination
        query = query.offset((current_page - 1) * items_per_page).limit(items_per_page)
    
        # Load related event_dates
        query = query.options(joinedload(cls.event_dates))
    
        # Execute query and convert to model
        events = query.all()
        return [event._to_model() for event in events], total_count

    @classmethod
    def get_organizer_events(
        cls,
        organizer_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve events for a specific organizer with pagination, filtering, and sorting.
    
        Args:
            organizer_id (int): The ID of the organizer.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.
    
        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing the list of events and the total count.
        """
        db = get_db_session()
    
        # Start with a subquery to get the earliest date for each event
        date_subquery = (
            db.query(EventDate.event_id, func.min(EventDate.date).label('min_date'))
            .group_by(EventDate.event_id)
            .subquery()
        )
    
        # Main query
        query = db.query(cls).filter(cls.organizer_id == organizer_id).join(date_subquery, cls.id == date_subquery.c.event_id)
    
        # Apply date range filter if provided
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params.pop("event_dates")
            if "date_from" in date_filters:
                query = query.filter(date_subquery.c.min_date >= date_filters["date_from"])
            if "date_to" in date_filters:
                query = query.filter(date_subquery.c.min_date <= date_filters["date_to"])
    
        # Apply additional filters using ParameterValidator
        if filter_params:
            query = ParameterValidator.apply_filters_and_sorting(
                query,
                cls,
                filter_params,
                None,  # We'll handle sorting separately
            )
    
        # Apply sorting
        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(
                            date_subquery.c.min_date.asc() if value == "asc" else date_subquery.c.min_date.desc()
                        )
                    else:
                        column = getattr(cls, key)
                        query = query.order_by(column.asc() if value == "asc" else column.desc())
        else:
            # Default sorting by earliest date
            query = query.order_by(date_subquery.c.min_date.asc())
    
        # Get total count of distinct events
        total_count = query.count()
    
        # Apply pagination
        query = query.offset((current_page - 1) * items_per_page).limit(items_per_page)
    
        # Load related event_dates
        query = query.options(joinedload(cls.event_dates))
    
        # Execute query and convert to model
        events = query.all()
        return [event._to_model() for event in events], total_count


class EventDate(Base):
    __tablename__ = "event_date"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)

    event = relationship("Event", back_populates="event_dates")
    reservations = relationship("Reservation", back_populates="event_date")

    def __init__(self, event_id: int, date: datetime, time: datetime, capacity: int):
        self.event_id = event_id
        self.date = date
        self.time = time
        self.capacity = capacity
        self.available_spots = capacity

    def book_seats(self, seats: int) -> bool:
        if self.available_spots >= seats:
            self.available_spots -= seats
            return True
        return False

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "date": self.date,
            "time": self.time,
            "capacity": self.capacity,
            "available_spots": self.available_spots,
        }
    
    @classmethod
    def get_event_date_by_id(cls, event_date_id: int) -> Optional['EventDate']:
        """
        Retrieve an event date by its ID.

        This class method queries the database to find an EventDate instance
        with the given ID. If found, it returns the EventDate object;
        otherwise, it returns None.

        Args:
            event_date_id (int): The unique identifier of the event date to retrieve.

        Returns:
            Optional[EventDate]: The EventDate object if found, None otherwise.

        Raises:
            Exception: If there's an error during the database query.
        """
        try:
            with get_db_session() as db:
                event_date = db.query(cls).filter(cls.id == event_date_id).first()
                return event_date
        except Exception as e:
            # Log the error here if you have a logging system
            print(f"Error retrieving event date: {str(e)}")
            raise
