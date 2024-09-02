import app.api.v1.endpoints
from app.utils.exceptions import CustomBadRequestException
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
    Boolean,
    text,
    select
)
from sqlalchemy.orm import relationship, joinedload
from datetime import date, datetime, time, timedelta
from app.database import Base
from app.models.event import (
    ClaimStatus,
    ClaimType,
    EventCreateModel,
    EventStatus,
    EventType,
    EventUpdateModel,
    TargetGroup,
)
from app.context_manager import get_db_session
from app.models.get_params import ParameterValidator
import typing
from app.data_adapter.attachment import Attachment
from app.data_adapter.waiting_list import WaitingList
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.exc import SQLAlchemyError



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
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.PUBLISHED)
    event_type = Column(SAEnum(EventType), nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in minutes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organizer_id = Column(Integer, ForeignKey("user.user_id"))
    more_info_url = Column(
        String(255), nullable=True
    )  # New field for additional information URL
    ztp_access = Column(Boolean, default=False, nullable=False)
    parking_spaces = Column(Integer, default=0, nullable=False)

    district = Column(String(100), nullable=False)  # New field
    region = Column(String(100), nullable=False)  # New field

    # Relationships remain the same
    attachments = relationship(
        "Attachment", back_populates="event", cascade="all, delete-orphan"
    )
    organizer = relationship("User", back_populates="organized_events")
    event_dates = relationship(
        "EventDate", back_populates="event", cascade="all, delete-orphan"
    )
    reservations = relationship("Reservation", back_populates="event")
    waiting_list = relationship("WaitingList", back_populates="event")
    claims = relationship("EventClaim", back_populates="event")

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
            "parent_info": None if self.parent_info is "null" else self.parent_info,
            "target_group": self.target_group,
            "age_from": self.age_from,
            "age_to": self.age_to,
            "status": self.status,
            "event_type": self.event_type,
            "duration": self.duration,
            "more_info_url": None if self.more_info_url == "null" else self.more_info_url,
            "attachments": [attachment._to_model() for attachment in self.attachments],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organizer_id": self.organizer_id,
            "ztp_access": self.ztp_access,
            "parking_spaces": self.parking_spaces,
            "event_dates": [event_date._to_model() for event_date in self.event_dates],
            "claims": [claim._to_model() for claim in self.claims],
            "district": self.district,
            "region": self.region,
        }


    Reservation = None

    @classmethod
    def create_new_event(
        cls, event_data: EventCreateModel, attachments: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        with get_db_session() as db:
            try:
                # Create the Event object without event_dates
                new_event = cls(
                    **event_data.dict(exclude={"attachments", "event_dates"})
                )
                new_event.available_spots = new_event.capacity

                # Add the new event to the session and flush to get the id
                db.add(new_event)
                db.flush()

                # Now create and add EventDate objects
                for event_date in event_data.event_dates:
                    # Combine date and time into a single datetime object
                    combined_datetime = datetime.combine(
                        event_date.date, event_date.time
                    )
                    new_event_date = EventDate(
                        event_id=new_event.id,
                        date=combined_datetime,  # Use the combined datetime for the date column
                        time=combined_datetime,  # Use the combined datetime for the time column
                        capacity=new_event.capacity,
                    )
                    db.add(new_event_date)

                # Handle attachments if any
                if attachments:
                    for attachment_data in attachments:
                        attachment = Attachment(**attachment_data, event=new_event)
                        db.add(attachment)

                # Commit the transaction
                db.commit()
                db.refresh(new_event)

                return new_event._to_model()
            except Exception as e:
                db.rollback()
                print(f"Error creating event: {str(e)}")
                raise CustomBadRequestException("Invalid data: " + str(e))

    @classmethod
    def update_event_by_id(
        cls,
        event_id: int,
        event_data: EventUpdateModel,
        existing_attachment_ids: List[int],
        new_attachments: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        db = get_db_session()
        try:
            event = db.query(cls).filter(cls.id == event_id).with_for_update().first()
            if not event:
                return None

            update_data = event_data.dict(exclude_unset=True)

            # Handle attachments
            existing_attachments = db.query(Attachment).filter(Attachment.event_id == event_id).all()
            for attachment in existing_attachments:
                if attachment.id not in existing_attachment_ids:
                    db.delete(attachment)
            for attachment_data in new_attachments:
                new_attachment = Attachment(**attachment_data, event_id=event_id)
                db.add(new_attachment)

            # Handle event dates
            if "event_dates" in update_data:
                existing_dates = db.query(EventDate).filter(EventDate.event_id == event_id).all()
                existing_date_ids = {date.id for date in existing_dates}
                update_date_ids = {date['id'] for date in update_data["event_dates"] if 'id' in date}

                # Update existing dates and add new ones
                for date_data in update_data["event_dates"]:
                    try:
                        date_obj = datetime.strptime(date_data["date"], "%Y-%m-%d").date() if isinstance(date_data["date"], str) else date_data["date"]
                        time_obj = datetime.strptime(date_data["time"], "%H:%M").time() if isinstance(date_data["time"], str) else date_data["time"]
                        combined_datetime = datetime.combine(date_obj, time_obj)

                        if 'id' in date_data and date_data['id'] in existing_date_ids:
                            # Update existing date
                            db.query(EventDate).filter(EventDate.id == date_data['id']).update({
                                'date': combined_datetime,
                                'time': combined_datetime,
                                'capacity': event.capacity,
                                'available_spots': date_data.get('available_spots', event.capacity),
                            })
                        else:
                            # Add new date
                            new_event_date = EventDate(
                                event_id=event_id,
                                date=combined_datetime,
                                time=combined_datetime,
                                capacity=event.capacity,
                                available_spots=date_data.get('available_spots', event.capacity),
                            )
                            db.add(new_event_date)
                    except (ValueError, TypeError) as e:
                        print(f"Error parsing date or time: {str(e)}")
                        raise CustomBadRequestException(f"Invalid date or time format: {str(e)}")

                # Remove dates that are no longer in the update data
                for date in existing_dates:
                    if date.id not in update_date_ids:
                        # Check if there are any reservations for this date
                        reservation_count = db.execute(
                            select(text("COUNT(*)"))
                            .select_from(text("reservation"))
                            .where(text("event_date_id = :date_id")),
                            {"date_id": date.id}
                        ).scalar()

                        if reservation_count == 0:
                            db.delete(date)
                        else:
                            print(f"Cannot delete event date (ID: {date.id}) as it has existing reservations.")

            # Update other fields only if they exist in the update_data and are not None
            for field, value in update_data.items():
                if field not in ["attachments", "event_dates"] and value is not None:
                    setattr(event, field, value)

            db.flush()
            db.refresh(event)
            result = event._to_model()

            db.commit()
            return result

        except SQLAlchemyError as e:
            db.rollback()
            print(f"Database error: {str(e)}")
            raise CustomBadRequestException(f"Database error: {str(e)}")
        except Exception as e:
            db.rollback()
            print(f"Error updating event: {str(e)}")
            raise CustomBadRequestException(f"Error updating event: {str(e)}")
        finally:
            db.close()



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
        db = get_db_session()

        query = db.query(cls, EventDate).join(EventDate, cls.id == EventDate.event_id)

        if filter_params:
            if "event_dates" in filter_params:
                date_filters = filter_params["event_dates"]
                if "date_from" in date_filters:
                    query = query.filter(EventDate.date >= datetime.strptime(date_filters["date_from"], "%Y-%m-%d").date())
                if "date_to" in date_filters:
                    # Add one day to the end date to include the entire last day
                    end_date = datetime.strptime(date_filters["date_to"], "%Y-%m-%d").date() + timedelta(days=1)
                    query = query.filter(EventDate.date < end_date)

            query = ParameterValidator.apply_filters_and_sorting(
                query,
                cls,
                {k: v for k, v in filter_params.items() if k != "event_dates"},
                None,
            )

        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(
                            EventDate.date.asc(), EventDate.time.asc() if value == "asc" 
                            else EventDate.date.desc(), EventDate.time.desc()
                        )
                    elif hasattr(cls, key):
                        column = getattr(cls, key)
                        query = query.order_by(
                            column.asc() if value == "asc" else column.desc()
                        )
        else:
            query = query.order_by(EventDate.date.asc(), EventDate.time.asc())

        total_count = query.count()

        all_results = query.all()

        all_events = []
        for event, event_date in all_results:
            event_dict = event._to_model()
            event_dict['event_date'] = event_date.date
            event_dict['event_time'] = event_date.time
            event_dict['current_event_date_id'] = event_date.id
            event_dict['is_current_event_date_locked'] = event_date.is_locked() 
            all_events.append(event_dict)

        sorted_events = sorted(all_events, key=lambda x: (x['event_date'], x['event_time']))

        start_index = (current_page - 1) * items_per_page
        end_index = start_index + items_per_page
        paginated_events = sorted_events[start_index:end_index]

        return paginated_events, total_count
    
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
            db.query(EventDate.event_id, func.min(EventDate.date).label("min_date"))
            .group_by(EventDate.event_id)
            .subquery()
        )

        # Main query
        query = (
            db.query(cls)
            .filter(cls.organizer_id == organizer_id)
            .join(date_subquery, cls.id == date_subquery.c.event_id)
        )

        # Apply date range filter if provided
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params.pop("event_dates")
            if "date_from" in date_filters:
                query = query.filter(
                    date_subquery.c.min_date >= date_filters["date_from"]
                )
            if "date_to" in date_filters:
                query = query.filter(
                    date_subquery.c.min_date <= date_filters["date_to"]
                )

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
                            date_subquery.c.min_date.asc()
                            if value == "asc"
                            else date_subquery.c.min_date.desc()
                        )
                    else:
                        column = getattr(cls, key)
                        query = query.order_by(
                            column.asc() if value == "asc" else column.desc()
                        )
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
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)
    lock_time_hours = Column(
        Integer, nullable=False, default=48
    )  # Store lock time as hours

    event = relationship("Event", back_populates="event_dates")
    reservations = relationship("Reservation", back_populates="event_date")
    waiting_list = relationship("WaitingList", back_populates="event_date")
    claims = relationship("EventClaim", back_populates="event_date", cascade="all, delete-orphan")

    def __init__(
        self,
        event_id: int,
        date: datetime,
        time: datetime,
        capacity: int,
        lock_time_hours: int = 48,
        available_spots: Optional[int] = None,
    ):
        self.event_id = event_id
        self.date = date
        self.time = time
        self.capacity = capacity
        self.available_spots = capacity
        self.lock_time_hours = lock_time_hours
        self.available_spots = available_spots if available_spots is not None else capacity

    def calculate_lock_time(self) -> datetime:
        """
        Calculate the lock time dynamically based on the event's date, time, and lock_time_hours.
        """
        event_datetime = datetime.combine(self.date, self.time.time())
        return event_datetime - timedelta(hours=self.lock_time_hours)

    def is_locked(self) -> bool:
        """
        Check if the event date is locked based on the current time and calculated lock time.
        """
        current_time = datetime.now()
        return current_time >= self.calculate_lock_time()

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
            "is_locked": self.is_locked(),
        }

    @classmethod
    def get_event_date_by_id(cls, event_date_id: int) -> Optional["EventDate"]:
        """
        Retrieve an event date by its ID, including locked event dates.

        Args:
            event_date_id (int): The unique identifier of the event date to retrieve.

        Returns:
            Optional[EventDate]: The EventDate object if found, None otherwise.
        """
        try:
            with get_db_session() as db:
                event_date = db.query(cls).filter(cls.id == event_date_id).first()
                return event_date
        except Exception as e:
            # Log the error here if you have a logging system
            print(f"Error retrieving event date: {str(e)}")
            return None




# Create EventClaim model
class EventClaim(Base):
    """
    Represents a claim for cancelling an event date or deleting an event.
    """
    __tablename__ = "event_claim"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    event_date_id = Column(Integer, ForeignKey("event_date.id"), nullable=True)
    organizer_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    claim_type = Column(SAEnum(ClaimType), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SAEnum(ClaimStatus), nullable=False, default=ClaimStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("Event", back_populates="claims")
    event_date = relationship("EventDate", back_populates="claims")

    @classmethod
    def create_claim(cls, claim_data: Dict[str, Any]) -> "EventClaim":
        """
        Create a new claim in the database.

        Args:
            claim_data (Dict[str, Any]): Data for creating the claim.

        Returns:
            EventClaim: The created claim object.
        """
        with get_db_session() as db:
            new_claim = cls(**claim_data)
            db.add(new_claim)
            db.commit()
            db.refresh(new_claim)
            return new_claim

    @classmethod
    def get_pending_claims(cls) -> List["EventClaim"]:
        """
        Retrieve all pending claims from the database.

        Returns:
            List[EventClaim]: A list of pending claim objects.
        """
        with get_db_session() as db:
            return db.query(cls).filter(cls.status == ClaimStatus.PENDING).all()

    @classmethod
    def update_claim_status(cls, claim_id: int, new_status: ClaimStatus) -> Optional["EventClaim"]:
        """
        Update the status of a claim in the database.

        Args:
            claim_id (int): The ID of the claim to update.
            new_status (ClaimStatus): The new status to set for the claim.

        Returns:
            Optional[EventClaim]: The updated claim object, or None if not found.
        """
        with get_db_session() as db:
            claim = db.query(cls).filter(cls.id == claim_id).first()
            if claim:
                claim.status = new_status
                db.commit()
                db.refresh(claim)
            return claim

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the EventClaim object to a dictionary representation.

        Returns:
            Dict[str, Any]: A dictionary containing the claim's data.
        """
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_date_id": self.event_date_id,
            "organizer_id": self.organizer_id,
            "claim_type": self.claim_type,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }