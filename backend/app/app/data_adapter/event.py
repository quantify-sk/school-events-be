import base64
import json
import os
from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    DateTime,
    JSON,
    Text,
    Enum as SAEnum,
    ForeignKey
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
from typing import List, Dict, Optional, Tuple, Union, Any
from sqlalchemy import func


class Event(Base):
    """
    Represents an event in the system.

    This class defines the structure and behavior of event objects, including
    database schema, initialization, and various operations like creation,
    updating, and retrieval.
    """

    __tablename__ = "event"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic event information
    title = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Capacity and availability
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)

    # Detailed information
    description = Column(Text)
    annotation = Column(String(500))  # Short description or annotation

    # Classification
    target_group = Column(SAEnum(TargetGroup), nullable=False)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.SCHEDULED)
    event_type = Column(SAEnum(EventType), nullable=False)

    # Additional information
    duration = Column(Float, nullable=False)  # in hours
    parent_info = Column(Text)

    # Attachments and timestamps
    attachments = Column(JSON)  # Stores a list of dictionaries with file info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Add a foreign key to link the event to its organizer
    organizer_id = Column(Integer, ForeignKey('user.user_id'))
    
    # Add a relationship to the User model
    organizer = relationship("User", back_populates="organized_events")

    def __init__(
        self,
        title: str,
        date: datetime,
        time: datetime,
        address: str,
        city: str,
        latitude: float,
        longitude: float,
        capacity: int,
        description: str = "",
        annotation: str = "",
        target_group: TargetGroup = TargetGroup.ALL,
        status: EventStatus = EventStatus.SCHEDULED,
        event_type: EventType = EventType.OTHER,
        duration: float = 1.0,
        parent_info: str = "",
        organizer_id: int = None,
        attachments: List[Dict[str, str]] = None,
    ):
        """
        Initialize a new Event instance.

        Args:
            title (str): The title of the event.
            date (datetime): The date of the event.
            time (datetime): The time of the event.
            address (str): The address of the event.
            city (str): The city where the event takes place.
            latitude (float): The latitude coordinate of the event location.
            longitude (float): The longitude coordinate of the event location.
            capacity (int): The total capacity of the event.
            description (str, optional): A detailed description of the event. Defaults to "".
            annotation (str, optional): A short description or annotation of the event. Defaults to "".
            target_group (TargetGroup, optional): The target group for the event. Defaults to TargetGroup.ALL.
            status (EventStatus, optional): The status of the event. Defaults to EventStatus.SCHEDULED.
            event_type (EventType, optional): The type of the event. Defaults to EventType.OTHER.
            duration (float, optional): The duration of the event in hours. Defaults to 1.0.
            parent_info (str, optional): Additional parent information. Defaults to "".
            attachments (List[Dict[str, str]], optional): List of attachment information. Defaults to None.
        """
        self.title = title
        self.date = date
        self.time = time
        self.address = address
        self.city = city
        self.latitude = latitude
        self.longitude = longitude
        self.capacity = capacity
        self.available_spots = capacity
        self.description = description
        self.annotation = annotation
        self.target_group = target_group
        self.status = status
        self.event_type = event_type
        self.duration = duration
        self.parent_info = parent_info
        self.attachments = attachments or []
        self.organizer_id = organizer_id

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the Event instance to a dictionary representation.

        Returns:
            Dict[str, Any]: A dictionary containing all event attributes.
        """
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
            "attachments": self._get_attachment_data(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organizer_id": self.organizer_id
        }

    def _get_attachment_data(self) -> List[Dict[str, str]]:
        """
        Retrieve attachment data, including base64 encoded file content.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing attachment information and data.
        """
        if not self.attachments:
            return []

        attachment_data = []
        for attachment in self.attachments:
            file_path = attachment.get("path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as file:
                    file_data = file.read()
                    base64_data = base64.b64encode(file_data).decode("utf-8")
                    attachment_data.append(
                        {
                            "name": attachment.get("name"),
                            "type": attachment.get("type"),
                            "data": base64_data,
                        }
                    )
        return attachment_data

    @classmethod
    def create_new_event(
        cls, event_data: EventCreateModel, attachments: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new event in the database.

        Args:
            event_data (EventCreateModel): The data for the new event.
            attachments (List[Dict[str, str]], optional): List of attachment information. Defaults to None.

        Returns:
            Dict[str, Any]: The created event as a dictionary.
        """
        db = get_db_session()
        new_event = cls(
            **event_data.dict(),
            status=EventStatus.SCHEDULED,
            attachments=attachments or [],
        )
        new_event.available_spots = new_event.capacity
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        return new_event._to_model()

    @classmethod
    def update_event_by_id(
        cls,
        event_id: int,
        event_data: EventUpdateModel,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing event by ID.
    
        Args:
            event_id (int): The ID of the event to update.
            event_data (EventUpdateModel): The updated event data.
    
        Returns:
            Optional[Dict[str, Any]]: The updated event as a dictionary, or None if the event was not found.
        """
        db = get_db_session()
        event = db.query(cls).filter(cls.id == event_id).first()
        if event:
            update_data = event_data.dict(exclude_unset=True)
            for field, value in update_data.items():
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
        """
        Delete an event by its ID.

        Args:
            event_id (int): The ID of the event to delete.

        Returns:
            bool: True if the event was successfully deleted, False otherwise.
        """
        db = get_db_session()
        event = db.query(cls).filter(cls.id == event_id).first()
        if event:
            db.delete(event)
            db.commit()
            return True
        return False

    @classmethod
    def get_event_by_id(cls, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve an event by its ID.

        Args:
            event_id (int): The ID of the event to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The event as a dictionary if found, None otherwise.
        """
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
        """
        Retrieve a paginated list of events with optional filtering and sorting.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): Filtering parameters.
            sorting_params (Optional[List[Dict[str, str]]]): Sorting parameters.
            date_from (Optional[datetime]): Start date for filtering events.
            date_to (Optional[datetime]): End date for filtering events.
            coordinates (Optional[str]): Coordinates for filtering events (format: latitude,longitude).
            radius (Optional[float]): Radius in kilometers for location-based filtering.

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing the list of events and the total count.
        """
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
        """
        Get events for a specific organizer with pagination, filtering, and sorting.

        Args:
            organizer_id (int): The ID of the organizer.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.
            date_from (Optional[datetime]): Start date for filtering events.
            date_to (Optional[datetime]): End date for filtering events.
            coordinates (Optional[str]): Coordinates for filtering events (format: latitude,longitude).
            radius (Optional[float]): Radius in kilometers for location-based filtering.

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing the list of events as dictionaries and the total count.
        """
        from app.context_manager import get_db_session

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
            lat, lon = map(float, coordinates.split(','))
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