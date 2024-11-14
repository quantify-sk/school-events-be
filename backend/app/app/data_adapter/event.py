import base64
from collections import defaultdict
import app.api.v1.endpoints
from app.utils.exceptions import CustomBadRequestException
from app.models.report import ReportType
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
    select,
)
from app.logger import logger
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
    EventDateModel,
)
from app.context_manager import get_db_session
from app.models.get_params import ParameterValidator, parse_json_params
import typing
from app.data_adapter.attachment import Attachment
from app.data_adapter.waiting_list import WaitingList
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.data_adapter.school import School
from app.models.statistics import StatisticsRequestModel
from sqlalchemy import Enum, JSON
from sqlalchemy.ext.hybrid import hybrid_property


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
            "more_info_url": None
            if self.more_info_url == "null"
            else self.more_info_url,
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
    def get_events_with_dates(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
        admin: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_db_session()

        # Base query with DISTINCT to avoid duplicates
        query = db.query(cls, EventDate, Attachment).distinct(cls.id)
        query = query.join(EventDate, cls.id == EventDate.event_id)
        query = query.outerjoin(Attachment, cls.id == Attachment.event_id)

        # Apply filters for event dates if provided
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params["event_dates"]
            if "date_from" in date_filters:
                from_date = datetime.strptime(date_filters["date_from"], "%Y-%m-%d").date()
                query = query.filter(EventDate.date >= from_date)
            if "date_to" in date_filters:
                to_date = datetime.strptime(date_filters["date_to"], "%Y-%m-%d").date()
                query = query.filter(EventDate.date <= to_date)

            del filter_params["event_dates"]
        elif not admin:
            today = datetime.now().date()
            query = query.filter(EventDate.date >= today)

        # Apply other filters and sorting
        if filter_params:
            query = ParameterValidator.apply_filters_and_sorting(query, cls, filter_params, None)

        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(EventDate.date.desc(), EventDate.time.desc())
        else:
            query = query.order_by(EventDate.date.desc(), EventDate.time.desc())

        # Count total results for pagination
        total_count = query.count()

        # Apply pagination
        query = query.limit(items_per_page).offset((current_page - 1) * items_per_page)

        # Execute the query
        all_results = query.all()

        # Process results
        all_events = []
        event_attachments = {}

        for event, event_date, attachment in all_results:
            event_dict = event._to_model()


            # Handle attachments
            if attachment is not None:
                if event_dict["id"] not in event_attachments:
                    with open(attachment.path, "rb") as file:
                        file_data = file.read()
                    event_attachments[event_dict["id"]] = {
                        "id": attachment.id,
                        "name": attachment.name,
                        "data": base64.b64encode(file_data).decode("utf-8") if not admin else None,
                        "type": attachment.type,
                    }

            all_events.append(event_dict)

        # Attachments processing
        for event_dict in all_events:
            event_dict["attachments"] = (
                [event_attachments.get(event_dict["id"])]
                if event_dict["id"] in event_attachments else []
            )

        return all_events, total_count

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
            existing_attachments = (
                db.query(Attachment).filter(Attachment.event_id == event_id).all()
            )
            for attachment in existing_attachments:
                if attachment.id not in existing_attachment_ids:
                    db.delete(attachment)
            for attachment_data in new_attachments:
                new_attachment = Attachment(**attachment_data, event_id=event_id)
                db.add(new_attachment)

            # Handle event dates
            if "event_dates" in update_data:
                existing_dates = (
                    db.query(EventDate).filter(EventDate.event_id == event_id).all()
                )
                existing_date_ids = {date.id for date in existing_dates}
                update_date_ids = {
                    date["id"] for date in update_data["event_dates"] if "id" in date
                }

                # Update existing dates and add new ones
                for date_data in update_data["event_dates"]:
                    try:
                        date_obj = (
                            datetime.strptime(date_data["date"], "%Y-%m-%d").date()
                            if isinstance(date_data["date"], str)
                            else date_data["date"]
                        )
                        time_obj = (
                            datetime.strptime(date_data["time"], "%H:%M").time()
                            if isinstance(date_data["time"], str)
                            else date_data["time"]
                        )
                        combined_datetime = datetime.combine(date_obj, time_obj)

                        if "id" in date_data and date_data["id"] in existing_date_ids:
                            # Update existing date
                            db.query(EventDate).filter(
                                EventDate.id == date_data["id"]
                            ).update(
                                {
                                    "date": combined_datetime,
                                    "time": combined_datetime,
                                    "capacity": event.capacity,
                                    "available_spots": date_data.get(
                                        "available_spots", event.capacity
                                    ),
                                }
                            )
                        else:
                            # Add new date
                            new_event_date = EventDate(
                                event_id=event_id,
                                date=combined_datetime,
                                time=combined_datetime,
                                capacity=event.capacity,
                                available_spots=date_data.get(
                                    "available_spots", event.capacity
                                ),
                            )
                            db.add(new_event_date)
                    except (ValueError, TypeError) as e:
                        print(f"Error parsing date or time: {str(e)}")
                        raise CustomBadRequestException(
                            f"Invalid date or time format: {str(e)}"
                        )

                # Remove dates that are no longer in the update data
                for date in existing_dates:
                    if date.id not in update_date_ids:
                        # Check if there are any reservations for this date
                        reservation_count = db.execute(
                            select(text("COUNT(*)"))
                            .select_from(text("reservation"))
                            .where(text("event_date_id = :date_id")),
                            {"date_id": date.id},
                        ).scalar()

                        if reservation_count == 0:
                            db.delete(date)
                        else:
                            print(
                                f"Cannot delete event date (ID: {date.id}) as it has existing reservations."
                            )

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
        admin: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_db_session()

        query = db.query(cls, EventDate, Attachment)
        query = query.join(EventDate, cls.id == EventDate.event_id)
        query = query.outerjoin(Attachment, cls.id == Attachment.event_id)

        # Handle event_dates manually
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params["event_dates"]
            if "date_from" in date_filters:
                from_date = datetime.strptime(
                    date_filters["date_from"], "%Y-%m-%d"
                ).date()
                query = query.filter(EventDate.date >= from_date)
            if "date_to" in date_filters:
                to_date = datetime.strptime(date_filters["date_to"], "%Y-%m-%d").date()
                query = query.filter(EventDate.date <= to_date)

            # Remove event_dates from filter_params to avoid processing it again
            del filter_params["event_dates"]
        elif not admin:
            # If not admin and no date filters, show only future events
            today = datetime.now().date()
            query = query.filter(EventDate.date >= today)

        # Use ParameterValidator for other filters
        if filter_params:
            query = ParameterValidator.apply_filters_and_sorting(
                query, cls, filter_params, None
            )

        # Handle sorting separately
        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(
                            EventDate.date.asc()
                            if value == "asc"
                            else EventDate.date.desc(),
                            EventDate.time.asc()
                            if value == "asc"
                            else EventDate.time.desc(),
                        )
                    elif hasattr(cls, key):
                        column = getattr(cls, key)
                        query = query.order_by(
                            column.asc() if value == "asc" else column.desc()
                        )
        else:
            query = query.order_by(EventDate.date.asc(), EventDate.time.asc())

        # Count total results
        total_count = query.count()

        # Apply pagination
        query = query.limit(items_per_page).offset((current_page - 1) * items_per_page)

        # Execute query
        all_results = query.all()

        # Process results
        all_events = []
        event_attachments = {}

        for event, event_date, attachment in all_results:
            event_dict = event._to_model()
            event_dict["event_date"] = event_date.date
            event_dict["event_time"] = event_date.time
            event_dict["current_event_date_id"] = event_date.id
            event_dict["is_current_event_date_locked"] = event_date.is_locked()
            event_dict["event_date_status"] = event_date.status

            event_id = event_dict["id"]

            if attachment is not None:
                if event_id not in event_attachments:
                    with open(attachment.path, "rb") as file:
                        file_data = file.read()
                    event_attachments[event_id] = {
                        "id": attachment.id,
                        "name": attachment.name,
                        "data": base64.b64encode(file_data).decode("utf-8")
                        if not admin
                        else None,
                        "type": attachment.type,
                    }

            all_events.append(event_dict)

        for event_dict in all_events:
            event_dict["attachments"] = (
                [event_attachments.get(event_dict["id"])]
                if event_dict["id"] in event_attachments
                else []
            )

        return all_events, total_count

    @classmethod
    def get_organizer_events(
        cls,
        organizer_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        db = get_db_session()
    
        query = db.query(cls, EventDate, Attachment)
        query = query.join(EventDate, cls.id == EventDate.event_id)
        query = query.outerjoin(Attachment, cls.id == Attachment.event_id)
        query = query.filter(cls.organizer_id == organizer_id)
    
        # Handle event_dates manually
        if filter_params and "event_dates" in filter_params:
            date_filters = filter_params["event_dates"]
            if "date_from" in date_filters:
                from_date = datetime.strptime(
                    date_filters["date_from"], "%Y-%m-%d"
                ).date()
                query = query.filter(EventDate.date >= from_date)
            if "date_to" in date_filters:
                to_date = datetime.strptime(date_filters["date_to"], "%Y-%m-%d").date()
                query = query.filter(EventDate.date <= to_date)
    
            # Remove event_dates from filter_params to avoid processing it again
            del filter_params["event_dates"]
    
        # Use ParameterValidator for other filters
        if filter_params:
            query = ParameterValidator.apply_filters_and_sorting(
                query, cls, filter_params, None
            )
    
        # Handle sorting separately
        if sorting_params:
            for sort_param in sorting_params:
                for key, value in sort_param.items():
                    if key == "event_dates.date":
                        query = query.order_by(
                            EventDate.date.asc()
                            if value == "asc"
                            else EventDate.date.desc(),
                            EventDate.time.asc()
                            if value == "asc"
                            else EventDate.time.desc(),
                        )
                    elif hasattr(cls, key):
                        column = getattr(cls, key)
                        query = query.order_by(
                            column.asc() if value == "asc" else column.desc()
                        )
        else:
            query = query.order_by(EventDate.date.asc(), EventDate.time.asc())
    
        # Count total results
        total_count = query.count()
    
        # Apply pagination
        query = query.limit(items_per_page).offset((current_page - 1) * items_per_page)
    
        # Execute query
        all_results = query.all()
    
        # Process results
        all_events = []
        event_attachments = {}
    
        for event, event_date, attachment in all_results:
            event_dict = event._to_model()
            event_dict["event_date"] = event_date.date
            event_dict["event_time"] = event_date.time
            event_dict["current_event_date_id"] = event_date.id
            event_dict["is_current_event_date_locked"] = event_date.is_locked()
            event_dict["event_date_status"] = event_date.status
    
            event_id = event_dict["id"]
    
            if attachment is not None:
                if event_id not in event_attachments:
                    with open(attachment.path, "rb") as file:
                        file_data = file.read()
                    event_attachments[event_id] = {
                        "id": attachment.id,
                        "name": attachment.name,
                        "data": base64.b64encode(file_data).decode("utf-8"),
                        "type": attachment.type,
                    }
    
            all_events.append(event_dict)
    
        for event_dict in all_events:
            event_dict["attachments"] = (
                [event_attachments.get(event_dict["id"])]
                if event_dict["id"] in event_attachments
                else []
            )
    
        return all_events, total_count

    def _to_model_without_attachments(self) -> Dict[str, Any]:
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
            "more_info_url": None
            if self.more_info_url == "null"
            else self.more_info_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "organizer_id": self.organizer_id,
            "ztp_access": self.ztp_access,
            "parking_spaces": self.parking_spaces,
            "claims": [claim._to_model() for claim in self.claims],
            "district": self.district,
            "region": self.region,
        }

    @classmethod
    def _get_event_dates(cls, query):
        event_dates = (
            query.with_entities(cls.id, cls.title, EventDate.date)
            .order_by(cls.id, EventDate.date)
            .all()
        )

        # Group dates by event
        grouped_dates = {}
        for event_id, title, date in event_dates:
            if event_id not in grouped_dates:
                grouped_dates[event_id] = {"title": title, "dates": []}
            grouped_dates[event_id]["dates"].append(date.strftime("%Y-%m-%d"))

        return [
            {"id": event_id, "title": data["title"], "dates": data["dates"]}
            for event_id, data in grouped_dates.items()
        ]

    @classmethod
    def generate_statistics(
        cls, filters: StatisticsRequestModel, report_type: ReportType
    ) -> Dict[str, Any]:
        db = get_db_session()
        query = db.query(cls).join(EventDate, EventDate.event_id == cls.id)

        # Apply filters
        if filters.start_date:
            query = query.filter(EventDate.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(EventDate.date <= filters.end_date)
        if filters.region:
            query = query.filter(cls.region == filters.region)
        if filters.district:
            query = query.filter(cls.district == filters.district)
        if filters.event_type:
            query = query.filter(cls.event_type == filters.event_type)
        if filters.target_group:
            query = query.filter(cls.target_group == filters.target_group)
        if filters.organizer_id:
            query = query.filter(cls.organizer_id == filters.organizer_id)

        statistics = {"summary": {}, "details": {}, "charts": {}}
        from app.models.reservation import ReservationStatus
        from app.data_adapter.user import User
        from app.data_adapter.reservation import Reservation
        from sqlalchemy import func, case

        if report_type == ReportType.EVENT_SUMMARY:
            # Query for event summary
            event_summary = db.query(
                cls.id.label('event_id'),
                cls.title.label('event_title'),
                cls.institution_name,
                cls.organizer_id,
                func.concat(User.first_name, ' ', User.last_name).label('organizer_name'),
                cls.capacity.label('event_capacity'),
                cls.available_spots.label('event_available_spots'),
                cls.event_type,
                cls.target_group,
                cls.district,
                cls.region,
                EventDate.id.label('event_date_id'),
                func.to_char(EventDate.date, 'YYYY-MM-DD').label('formatted_date'),
                EventDate.capacity.label('date_capacity'),
                EventDate.available_spots.label('date_available_spots'),
                func.count(Reservation.id).label('reservation_count'),
                func.sum(case((Reservation.status == ReservationStatus.CONFIRMED, 1), else_=0)).label('confirmed_reservations'),
                func.sum(case((Reservation.status == ReservationStatus.CANCELLED, 1), else_=0)).label('cancelled_reservations'),
                func.sum(case((Reservation.status == ReservationStatus.PENDING, 1), else_=0)).label('pending_reservations')
            ).join(EventDate, EventDate.event_id == cls.id)\
             .outerjoin(Reservation, Reservation.event_date_id == EventDate.id)\
             .join(User, User.user_id == cls.organizer_id)

            # Apply date filters to the event_summary query
            if filters.start_date:
                event_summary = event_summary.filter(EventDate.date >= filters.start_date)
            if filters.end_date:
                event_summary = event_summary.filter(EventDate.date <= filters.end_date)

            event_summary = event_summary.group_by(
                cls.id, EventDate.id, User.user_id, User.first_name, User.last_name
            ).order_by(EventDate.date).all()

            event_summary_list = []
            total_events = 0
            total_reservations = 0
            total_capacity = 0
            category_counts = {}

            for row in event_summary:
                filled_spots = row.date_capacity - row.date_available_spots
                fill_rate = (filled_spots / row.date_capacity) * 100 if row.date_capacity > 0 else 0

                # Count categories
                category_counts[row.event_type] = category_counts.get(row.event_type, 0) + 1

                event_summary_list.append({
                    "event_id": row.event_id,
                    "event_title": row.event_title,
                    "institution_name": row.institution_name,
                    "organizer_id": row.organizer_id,
                    "organizer_name": row.organizer_name,
                    "event_capacity": row.event_capacity,
                    "event_available_spots": row.event_available_spots,
                    "filled_spots": filled_spots,
                    "fill_rate": round(fill_rate, 2),
                    "reservation_count": row.reservation_count,
                })

                # Aggregate totals
                total_events += 1
                total_reservations += row.reservation_count
                total_capacity += row.date_capacity

            # Calculate overall fill rate
            overall_fill_rate = (total_reservations / total_capacity) * 100 if total_capacity > 0 else 0


            # Dictionary to translate EventType labels to Slovak
            translation_dict = {
                EventType.THEATER: "Divadlo",
                EventType.CONCERT: "Koncert",
                EventType.EXHIBITION: "Výstava",
                EventType.WORKSHOP: "Workshop",
                EventType.SCREENING: "Premietanie",
                EventType.PERFORMANCE: "Predstavenie",
                EventType.DANCE: "Tanec",
                EventType.OPERA: "Opera",
                EventType.BALLET: "Balet",
                EventType.OTHER: "Iné"
            }

            # Translate labels from category_counts
            translated_labels = [translation_dict[EventType(category)] for category in category_counts.keys()]
            # Prepare chart data
            statistics["charts"] = {
                "totalEvents": {
                    "labels": ["Celkový počet podujatí"],
                    "data": [total_events]
                },
                "totalReservations": {
                    "labels": ["Celkový počet rezervácií"],
                    "data": [total_reservations]
                },
                "overallFillRate": {
                    "labels": ["Celková obsadenosť"],
                    "data": [round(overall_fill_rate, 2)]
                },
                "eventsByCategory": {
                    "labels": translated_labels,
                    "data": list(category_counts.values())
                }
            }

            statistics["details"]["event_summary"] = event_summary_list


        elif report_type == ReportType.RESERVATION:
            # Existing RESERVATION report logic
            total_reservations = cls._get_total_reservations(query)
            reservation_trends = cls._get_reservation_trends(db)
            reservation_status_distribution = cls._get_reservation_status_distribution(
                query
            )

            statistics["summary"] = {"total_reservations": total_reservations}

            statistics["details"] = {
                "reservation_trends": reservation_trends,
                "reservation_status_distribution": reservation_status_distribution,
            }

            statistics["charts"] = {
                "reservation_trends": {
                    "labels": list(reservation_trends.keys()),
                    "data": list(reservation_trends.values()),
                },
                "reservation_status_distribution": {
                    "labels": list(reservation_status_distribution.keys()),
                    "data": list(reservation_status_distribution.values()),
                },
            }

        else:
            raise ValueError(f"Unsupported report type: {report_type}")

        return statistics

    @staticmethod
    def _get_events_by_status(query):
        # Fetch count of events grouped by status
        return dict(
            query.with_entities(Event.status, func.count(Event.id))
            .group_by(Event.status)
            .all()
        )

    @staticmethod
    def _get_events_by_type(query):
        return dict(
            query.with_entities(Event.event_type, func.count(Event.id))
            .group_by(Event.event_type)
            .all()
        )

    @staticmethod
    def _get_events_by_target_group(query):
        return dict(
            query.with_entities(Event.target_group, func.count(Event.id))
            .group_by(Event.target_group)
            .all()
        )

    @staticmethod
    def _get_popular_events(query):
        from app.data_adapter.reservation import Reservation

        # Fetch popular events based on reservation count
        events = (
            query.join(Reservation, Reservation.event_id == Event.id)
            .group_by(Event.id)
            .order_by(func.count(Reservation.id).desc())
            .limit(10)
            .all()
        )
        return [event._to_model_without_attachments() for event in events]

    @staticmethod
    def _get_average_capacity(query):
        result = query.with_entities(func.avg(Event.capacity)).scalar()
        return float(result) if result is not None else 0

    @staticmethod
    def _get_total_reservations(query):
        from app.data_adapter.reservation import Reservation

        return (
            query.join(Reservation).with_entities(func.count(Reservation.id)).scalar()
        )

    @staticmethod
    def _get_reservation_status_distribution(query):
        from app.data_adapter.reservation import Reservation

        # Group reservation status and count them
        return dict(
            query.join(Reservation, Reservation.event_id == Event.id)
            .with_entities(Reservation.status, func.count(Reservation.id))
            .group_by(Reservation.status)
            .all()
        )

    @staticmethod
    def _get_events_by_region(query):
        return dict(
            query.with_entities(Event.region, func.count(Event.id))
            .group_by(Event.region)
            .all()
        )

    @staticmethod
    def _get_events_by_district(query):
        return dict(
            query.with_entities(Event.district, func.count(Event.id))
            .group_by(Event.district)
            .all()
        )

    @staticmethod
    def _get_highest_fill_rate_events(query):
        from app.data_adapter.reservation import Reservation

        # Order by fill rate (reservations/capacity)
        events = (
            query.join(Reservation)
            .group_by(Event.id)
            .order_by((func.count(Reservation.id) * 100 / Event.capacity).desc())
            .limit(10)
            .all()
        )
        return [event._to_model_without_attachments() for event in events]

    @staticmethod
    def _get_average_duration(query):
        result = query.with_entities(func.avg(Event.duration)).scalar()
        return float(result) if result is not None else 0

    @staticmethod
    def _get_events_with_parking(query):
        # Count events with available parking spaces
        return query.filter(Event.parking_spaces > 0).count()

    @staticmethod
    def _get_events_with_ztp_access(query):
        return query.filter(Event.ztp_access == True).count()

    @staticmethod
    def _get_average_age_range(query):
        avg_from = query.with_entities(func.avg(Event.age_from)).scalar()
        avg_to = query.with_entities(func.avg(Event.age_to)).scalar()
        return {
            "average_age_from": float(avg_from) if avg_from is not None else 0,
            "average_age_to": float(avg_to) if avg_to is not None else 0,
        }

    @staticmethod
    def _get_most_active_organizers(query):
        from app.data_adapter.user import User

        result = (
            query.join(User, Event.organizer_id == User.user_id)
            .group_by(User.user_id, User.first_name, User.last_name)
            .order_by(func.count(Event.id).desc())
            .with_entities(
                User.user_id,
                User.first_name,
                User.last_name,
                func.count(Event.id).label("event_count"),
            )
            .limit(10)
            .all()
        )
        return [
            {
                "user_id": row.user_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "event_count": row.event_count,
            }
            for row in result
        ]

    @staticmethod
    def _get_reservation_trends(session):
        from app.data_adapter.reservation import Reservation

        today = datetime.utcnow().date()
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        last_year = today - timedelta(days=365)

        trends = {
            "last_week": session.query(Reservation)
            .filter(Reservation.created_at >= last_week)
            .count(),
            "last_month": session.query(Reservation)
            .filter(Reservation.created_at >= last_month)
            .count(),
            "last_year": session.query(Reservation)
            .filter(Reservation.created_at >= last_year)
            .count(),
        }
        return trends

    @staticmethod
    def _get_school_participation(session):
        from app.data_adapter.reservation import Reservation
        from app.data_adapter.user import User
        from app.data_adapter.school import School

        school_query = (
            session.query(School)
            .join(User, User.school_id == School.id)
            .join(Reservation, Reservation.user_id == User.user_id)
        )

        total_schools = school_query.distinct(School.id).count()

        most_active_schools = (
            school_query.group_by(School.id, School.name)
            .order_by(func.count(Reservation.id).desc())
            .with_entities(
                School.id,
                School.name,
                func.count(Reservation.id).label("reservation_count"),
            )
            .limit(5)
            .all()
        )

        return {
            "total_participating_schools": total_schools,
            "most_active_schools": [
                {
                    "school_id": school.id,
                    "school_name": school.name,
                    "reservation_count": school.reservation_count,
                }
                for school in most_active_schools
            ],
        }


class EventDate(Base):
    __tablename__ = "event_date"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_spots = Column(Integer, nullable=False)
    lock_time_hours = Column(Integer, nullable=False, default=48)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.PUBLISHED)

    event = relationship("Event", back_populates="event_dates")
    reservations = relationship("Reservation", back_populates="event_date")
    waiting_list = relationship("WaitingList", back_populates="event_date")
    claims = relationship(
        "EventClaim", back_populates="event_date", cascade="all, delete-orphan"
    )
    @hybrid_property
    def total_attendees(self):
        from app.models.reservation import ReservationStatus
        return sum(
            reservation.number_of_students + reservation.number_of_teachers
            for reservation in self.reservations
            if reservation.status == ReservationStatus.CONFIRMED
        )

    

    def __init__(
        self,
        event_id: int,
        date: datetime,
        time: datetime,
        capacity: int,
        lock_time_hours: int = 48,
        available_spots: Optional[int] = None,
        status: EventStatus = EventStatus.PUBLISHED,
    ):
        self.event_id = event_id
        self.date = date
        self.time = time
        self.capacity = capacity
        self.lock_time_hours = lock_time_hours
        self.available_spots = (
            available_spots if available_spots is not None else capacity
        )
        self.status = status

    def calculate_lock_time(self) -> datetime:
        """
        Calculate the lock time dynamically based on the event's date, time, and lock_time_hours.
        """
        event_datetime = datetime.combine(self.date, self.time.time())
        return event_datetime - timedelta(hours=self.lock_time_hours)

    def update_status(self):
        """
        Update the status of the event based on the current time.
        """
        current_time = datetime.now()
        event_datetime = datetime.combine(self.date, self.time.time())
        if current_time > event_datetime:
            if self.status not in [
                EventStatus.COMPLETED,
                EventStatus.CANCELLED,
                EventStatus.COMPLETED_UNPAID,
                EventStatus.SENT_PAYMENT,
            ]:
                self.status = EventStatus.COMPLETED_UNPAID

    def is_locked(self) -> bool:
        """
        Check if the event date is locked based on the current time, calculated lock time, and status.
        """
        self.update_status()  # Ensure status is up-to-date before checking
        current_time = datetime.now()
        return current_time >= self.calculate_lock_time() or self.status in [
            EventStatus.COMPLETED,
            EventStatus.COMPLETED_UNPAID,
            EventStatus.CANCELLED,
            EventStatus.SENT_PAYMENT,
        ]

    def book_seats(self, seats: int) -> bool:
        """
        Book a specified number of seats for the event.
        """
        if self.available_spots >= seats:
            self.available_spots -= seats
            return True
        return False

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the EventDate instance to a dictionary representation.
        """
        self.update_status()  # Ensure status is up-to-date
        return {
            "id": self.id,
            "event_id": self.event_id,
            "date": self.date,
            "time": self.time,
            "capacity": self.capacity,
            "available_spots": self.available_spots,
            "is_locked": self.is_locked(),
            "status": self.status,
            "total_attendees": self.total_attendees,
        }

    @classmethod
    def get_event_date_by_id(cls, event_date_id: int) -> Optional["EventDate"]:
        """
        Retrieve an event date by its ID, including locked event dates.
        """
        try:
            with get_db_session() as db:
                event_date = (
                    db.query(cls)
                    .options(joinedload(cls.reservations))  # Eager load reservations
                    .filter(cls.id == event_date_id)
                    .first()
                )
                return event_date
        except Exception as e:
            print(f"Error retrieving event date: {str(e)}")
            return None

    @classmethod
    def update_past_event_statuses(cls, db: Session):
        """
        Update the status of all past events to COMPLETED_UNPAID if not already COMPLETED or CANCELLED.
        """
        print("Starting update_past_event_statuses")
        try:
            past_events = (
                db.query(cls)
                .filter(
                    cls.date < datetime.now(), cls.status.in_([EventStatus.PUBLISHED])
                )
                .all()
            )
            updated_count = 0
            for event in past_events:
                if event.status != EventStatus.COMPLETED_UNPAID:
                    event.status = EventStatus.COMPLETED_UNPAID
                    updated_count += 1
            db.commit()
            return updated_count, db
        except Exception as e:
            print(f"Error updating event statuses: {e}")
            db.rollback()
            return 0
        finally:
            print("Finished update_past_event_statuses")

    @classmethod
    def mark_as_paid(cls, event_date_id: int) -> bool:
        db = get_db_session()

        try:
            event_date = db.query(cls).filter(cls.id == event_date_id).first()
            if event_date:
                print("Event date found", event_date._to_model())
                event_date.status = EventStatus.SENT_PAYMENT
                print(f"Status after setting: {event_date.status}")
                db.flush()

                db.commit()
                db.refresh(event_date)
                print("Event date status updated", event_date._to_model())
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error marking event date as paid: {str(e)}")
            return False
        finally:
            db.close()

    @classmethod
    def mark_as_completed(cls, event_date_id: int) -> bool:
        db = get_db_session()

        try:
            event_date = db.query(cls).filter(cls.id == event_date_id).first()
            print("Event date found", event_date._to_model())
            if event_date:
                event_date.status = EventStatus.COMPLETED
                print(f"Status after setting: {event_date.status}")
                db.flush()
                db.commit()
                db.refresh(event_date)
                print("Event date status updated", event_date._to_model())
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Error marking event date as completed: {str(e)}")
            return False
        finally:
            db.close()


class EventClaim(Base):
    """
    Represents a claim for creating, updating, or cancelling an event or event date.
    """

    __tablename__ = "event_claim"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(
        Integer, ForeignKey("event.id"), nullable=True
    )  # Nullable for create claims
    event_date_id = Column(Integer, ForeignKey("event_date.id"), nullable=True)
    organizer_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    claim_type = Column(Enum(ClaimType), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    event_data = Column(
        JSON, nullable=True
    )  # Store event data for create/update claims

    event = relationship("Event", back_populates="claims", lazy='joined')
    event_date = relationship("EventDate", back_populates="claims", lazy='joined')

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
    def update_claim_status(
        cls, claim_id: int, new_status: ClaimStatus
    ) -> Optional["EventClaim"]:
        """
        Update the status of a claim in the database and process the claim if approved.

        Args:
            claim_id (int): The ID of the claim to update.
            new_status (ClaimStatus): The new status to set for the claim.

        Returns:
            Optional[EventClaim]: The updated claim object, or None if not found.
        """
        with get_db_session() as db:
            claim = db.query(cls).filter(cls.id == claim_id).first()
            if claim:
                if (
                    new_status == ClaimStatus.APPROVED
                    and claim.status != ClaimStatus.APPROVED
                ):
                    # Process the claim if it's being approved for the first time
                    if claim.claim_type == ClaimType.CREATE_EVENT:
                        cls._process_create_event(db, claim)
                    elif claim.claim_type == ClaimType.EDIT_EVENT:
                        cls._process_edit_event(db, claim)
                    elif claim.claim_type == ClaimType.DELETE_EVENT:
                        cls._process_delete_event(db, claim)
                    elif claim.claim_type == ClaimType.CANCEL_DATE:
                        cls._process_cancel_date(db, claim)
                    elif claim.claim_type == ClaimType.ADD_DATE:
                        cls._process_add_date(db, claim)

            claim.status = new_status
            claim.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(claim)
            return claim

    @classmethod
    def _process_create_event(cls, db: Session, claim: "EventClaim"):
        # Prepare event data
        event_data = claim.event_data.copy()
        
        # Add missing required fields
        event_data["institution_name"] = event_data.get("institution_name", "")
        event_data["organizer_id"] = claim.organizer_id
        
        # Handle dates
        dates = event_data.pop("eventDates", []) or event_data.pop("dates", [])
        event_data["event_dates"] = []  # Initialize empty dates list
        
        # Process attachments
        attachments = event_data.get("attachments", [])
        validated_attachments = []
        for attachment in attachments:
            if isinstance(attachment, dict) and "file" in attachment:
                file_data = attachment["file"]  # Extract file info, assuming "file" contains file data
                # Mock upload and storage process (e.g., upload file and get file path)
                file_path = f"/uploads/{file_data['name']}"  # Replace with actual upload logic
                validated_attachment = {
                    "name": file_data["name"],
                    "path": file_path,
                    "type": file_data.get("type", "unknown")
                }
                validated_attachments.append(validated_attachment)
        event_data["attachments"] = validated_attachments if validated_attachments else None
        
        # Create event model with validated data
        event_model = EventCreateModel(
            title=event_data["title"],
            institution_name=event_data["institution_name"],
            address=event_data["address"],
            city=event_data["city"],
            capacity=event_data["capacity"],
            description=event_data.get("description"),
            annotation=event_data.get("annotation"),
            parent_info=event_data.get("parent_info"),
            target_group=event_data["target_group"],
            age_from=event_data["age_from"],
            age_to=event_data.get("age_to"),
            event_type=event_data["event_type"],
            duration=event_data["duration"],
            organizer_id=event_data["organizer_id"],
            more_info_url=event_data.get("more_info_url"),
            attachments=event_data["attachments"],
            event_dates=[],  # Will be added later
            parking_spaces=event_data.get("parking_spaces"),
            ztp_access=event_data.get("ztp_access"),
            region=event_data.get("region"),
            district=event_data.get("district")
        )
        
        # Create new event excluding attachments and dates
        new_event = Event(**event_model.dict(exclude={"attachments", "event_dates"}))
        new_event.available_spots = new_event.capacity
        db.add(new_event)
        db.flush()  # Get the event ID
        
        # Process dates
        for date_entry in dates:
            date_obj = datetime.strptime(date_entry["date"], "%Y-%m-%d").date()
            time_obj = datetime.strptime(date_entry["time"], "%H:%M").time()
            combined_datetime = datetime.combine(date_obj, time_obj)
            
            new_event_date = EventDate(
                event_id=new_event.id,
                date=combined_datetime,
                time=combined_datetime,
                capacity=new_event.capacity,
                available_spots=new_event.capacity,
            )
            db.add(new_event_date)
        
        # Process validated attachments for DB storage
        if event_model.attachments:
            for attachment_data in event_model.attachments:
                attachment = Attachment(
                    event_id=new_event.id,
                    name=attachment_data["name"],
                    path=attachment_data["path"],
                    type=attachment_data["type"]
                )
                db.add(attachment)
        
        claim.event = new_event
        return new_event


    @classmethod
    def _process_edit_event(cls, db: Session, claim: "EventClaim"):
        event = claim.event
        if not event:
            raise ValueError("Event not found for edit claim")

        # Extract only the 'to' values from the claim.event_data
        update_data = {
            key: value["to"] for key, value in claim.event_data.items() if "to" in value
        }

        # Create EventUpdateModel instance with extracted 'to' values
        update_model = EventUpdateModel(**update_data)
        update_dict = update_model.dict(exclude_unset=True)

        for field, value in update_dict.items():
            if field not in ["attachments", "event_dates"] and value is not None:
                setattr(event, field, value)

        if "event_dates" in update_dict:
            cls._update_event_dates(db, event, update_dict["event_dates"])

        if "attachments" in update_dict:
            cls._update_attachments(db, event, update_dict["attachments"])

    @classmethod
    def _process_delete_event(cls, db: Session, claim: "EventClaim"):
        event = claim.event
        if not event:
            raise ValueError("Event not found for delete claim")
        db.delete(event)

    @classmethod
    def _process_cancel_date(cls, db: Session, claim: "EventClaim"):
        if not claim.event_data or "selected_dates" not in claim.event_data:
            raise ValueError("No selected dates found in claim data")

        selected_date_ids = claim.event_data["selected_dates"]
        for date_id in selected_date_ids:
            event_date = db.query(EventDate).filter(EventDate.id == date_id).first()
            if event_date:
                event_date.status = EventStatus.CANCELLED
            else:
                logger.warning(
                    f"Event date with id {date_id} not found for cancel claim {claim.id}"
                )

    @classmethod
    def _process_add_date(cls, db: Session, claim: "EventClaim"):
        """
        Process a claim of type 'add_date' to add new event dates.

        Args:
            db (Session): Database session.
            claim (EventClaim): The claim object to process.
        """
        if not claim.event_data or "new_dates" not in claim.event_data:
            raise ValueError("No new dates found in claim data")

        event = claim.event
        if not event:
            raise ValueError("Event not found for add date claim")

        for new_date in claim.event_data["new_dates"]:
            # Assuming new_date is a dict with 'date' and 'time' keys
            combined_datetime = datetime.combine(
                datetime.strptime(new_date["date"], "%Y-%m-%d"),  # Adjust date format as needed
                datetime.strptime(new_date["time"], "%H:%M").time()
            )

            # Create a new EventDate instance
            new_event_date = EventDate(
                event_id=event.id,
                date=combined_datetime,
                time=combined_datetime,
                capacity=event.capacity,
                available_spots=event.capacity,
            )
            db.add(new_event_date)

        # Optionally, update claim status to indicate processing is complete
        claim.status = ClaimStatus.APPROVED
        claim.updated_at = datetime.utcnow()

    @classmethod
    def _update_event_dates(
        cls, db: Session, event: Event, new_dates: List[EventDateModel]
    ):
        existing_dates = {date.id: date for date in event.event_dates}

        for date_data in new_dates:
            if date_data.id in existing_dates:
                existing_date = existing_dates[date_data.id]
                for field, value in date_data.dict(exclude={"id", "event_id"}).items():
                    setattr(existing_date, field, value)
            else:
                new_date = EventDate(
                    **date_data.dict(exclude={"id"}), event_id=event.id
                )
                db.add(new_date)

        for old_date_id in set(existing_dates.keys()) - set(
            date.id for date in new_dates
        ):
            db.delete(existing_dates[old_date_id])

    @classmethod
    def _update_attachments(
        cls, db: Session, event: Event, new_attachments: List[Attachment]
    ):
        existing_attachments = {
            attachment.id: attachment for attachment in event.attachments
        }

        for attachment_data in new_attachments:
            if attachment_data.id in existing_attachments:
                existing_attachment = existing_attachments[attachment_data.id]
                for field, value in attachment_data.dict(exclude={"id"}).items():
                    setattr(existing_attachment, field, value)
            else:
                new_attachment = Attachment(
                    **attachment_data.dict(exclude={"id"}), event_id=event.id
                )
                db.add(new_attachment)

        for old_attachment_id in set(existing_attachments.keys()) - set(
            attachment.id for attachment in new_attachments
        ):
            db.delete(existing_attachments[old_attachment_id])

    @classmethod
    def get_pending_claims(cls) -> List["EventClaim"]:
        """
        Retrieve all pending claims from the database.

        Returns:
            List[EventClaim]: A list of pending claim objects.
        """
        with get_db_session() as db:
            return db.query(cls).filter(cls.status == ClaimStatus.PENDING).all()

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
            "claim_type": self.claim_type.value,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "event_data": self.event_data,
        }
