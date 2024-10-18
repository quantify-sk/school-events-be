from app.data_adapter.school import School
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    and_,
    func,
    select,
    join,
)
from sqlalchemy.orm import relationship, joinedload, aliased
from datetime import date, datetime, timezone
from app.context_manager import get_db_session
from app.database import Base
from enum import Enum as PyEnum
from typing import List, Dict, Any
from app.utils.exceptions import CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from app.data_adapter.event import Event, EventDate
from app.data_adapter.reservation import Reservation
from app.models.get_params import ParameterValidator
import json
from app.models.reservation import ReservationStatus


class ReportType(PyEnum):
    EVENT_SUMMARY = "event_summary"
    ATTENDANCE = "attendance"
    RESERVATION = "reservation"


class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(Enum(ReportType), nullable=False)
    generated_on = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("user.user_id"))
    filters = Column(JSON, nullable=True)
    data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="reports")

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "report_type": self.report_type.value,
            "generated_on": self.generated_on.isoformat(),
            "generated_by": self.generated_by,
            "filters": self.filters,
            "data": self.data,
        }

    @staticmethod
    def serialize_datetime(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    @classmethod
    def create_report(
        cls, report_type: ReportType, generated_by: int, filters: dict, data: dict
    ) -> Dict[str, Any]:
        with get_db_session() as session:
            serialized_filters = json.dumps(filters, default=cls.serialize_datetime)
            serialized_data = json.dumps(data, default=cls.serialize_datetime)
            report = cls(
                report_type=report_type,
                generated_by=generated_by,
                filters=serialized_filters,
                data=serialized_data,
            )
            session.add(report)
            session.commit()
            return report._to_model()

    @classmethod
    def get_report_by_id(cls, report_id: int) -> Dict[str, Any]:
        with get_db_session() as session:
            report = session.query(cls).filter_by(id=report_id).first()
            if not report:
                raise CustomBadRequestException(ResponseMessages.ERR_REPORT_NOT_FOUND)
            return report._to_model()

    @classmethod
    def get_all_reports(cls) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            reports = session.query(cls).all()
            return [report._to_model() for report in reports]

    @classmethod
    def generate_report(cls, report_type: ReportType, filters: dict) -> Dict[str, Any]:
        report_data = None
        if report_type == ReportType.EVENT_SUMMARY:
            report_data = cls.generate_event_summary(filters)
        elif report_type == ReportType.ATTENDANCE:
            report_data = cls.generate_attendance_report(filters)
        elif report_type == ReportType.RESERVATION:
            report_data = cls.generate_reservation_report(filters)
        else:
            raise CustomBadRequestException(ResponseMessages.ERR_INVALID_REPORT_TYPE)

        return {
            "report_type": report_type.value,
            "filters": filters,
            "data": report_data,
        }

    @classmethod
    def generate_event_summary(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            query = (
                session.query(Event)
                .distinct()
                .options(joinedload(Event.event_dates), joinedload(Event.reservations))
            )

            # Handle date filtering separately
            if filters.get("start_date") or filters.get("end_date"):
                query = query.join(Event.event_dates)
                if filters.get("start_date"):
                    query = query.filter(
                        EventDate.date >= cls.ensure_utc(filters["start_date"])
                    )
                if filters.get("end_date"):
                    query = query.filter(
                        EventDate.date <= cls.ensure_utc(filters["end_date"])
                    )

            # Use ParameterValidator for other filters
            filter_params = {"multi_columns": []}
            if filters.get("event_type"):
                filter_params["multi_columns"].append(
                    {"event_type": [filters["event_type"]]}
                )
            if filters.get("city"):
                filter_params["multi_columns"].append({"city": [filters["city"]]})

            query = ParameterValidator.apply_filters_and_sorting(
                query, Event, filter_params, None
            )

            events = query.all()

            event_summaries = []
            for event in events:
                event_model = event._to_model()
                total_capacity = sum(date.capacity for date in event.event_dates)
                total_available_spots = sum(
                    date.available_spots for date in event.event_dates
                )
                total_reservations = len(event.reservations)
                event_model["total_capacity"] = total_capacity
                event_model["total_available_spots"] = total_available_spots
                event_model["total_reservations"] = total_reservations
                event_summaries.append(event_model)

            return event_summaries

    @classmethod
    def generate_attendance_report(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            current_time = datetime.utcnow()
            query = (
                session.query(
                    Event.id,
                    Event.title,
                    Event.institution_name,
                    Event.city,
                    Event.event_type,
                    EventDate.date,
                    func.count(Reservation.id).label("attendance_count"),
                )
                .join(EventDate, Event.id == EventDate.event_id)
                .outerjoin(
                    Reservation,
                    and_(
                        Reservation.event_id == Event.id,
                        Reservation.event_date_id == EventDate.id,
                    ),
                )
                .filter(EventDate.date <= current_time)
            )

            # Handle date filtering
            if filters.get("start_date"):
                query = query.filter(
                    EventDate.date >= cls.ensure_utc(filters["start_date"])
                )
            if filters.get("end_date"):
                query = query.filter(
                    EventDate.date <= cls.ensure_utc(filters["end_date"])
                )

            # Use ParameterValidator for other filters
            filter_params = {"multi_columns": []}
            if filters.get("event_type"):
                filter_params["multi_columns"].append(
                    {"event_type": [filters["event_type"]]}
                )
            if filters.get("city"):
                filter_params["multi_columns"].append({"city": [filters["city"]]})

            query = ParameterValidator.apply_filters_and_sorting(
                query, Event, filter_params, None
            )

            query = query.group_by(
                Event.id,
                Event.title,
                Event.institution_name,
                Event.city,
                Event.event_type,
                EventDate.date,
            )
            results = query.all()

            attendance_report = [
                {
                    "event_id": result.id,
                    "title": result.title,
                    "institution_name": result.institution_name,
                    "city": result.city,
                    "event_type": result.event_type,
                    "date": result.date.isoformat(),
                    "attendance_count": result.attendance_count,
                }
                for result in results
            ]

            return attendance_report

    @classmethod
    def generate_reservation_report(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            from app.data_adapter.user import User  # Lazy import
            from app.data_adapter.school import School  # Lazy import

            query = (
                session.query(Reservation)
                .join(EventDate)
                .join(Event)
                .join(User, Reservation.user_id == User.user_id)
                .outerjoin(School, User.school_id == School.id)
            )

            print(f"Filters: {filters}")  # Debug print

            # Apply date filters
            if filters.get("start_date"):
                query = query.filter(
                    EventDate.date >= cls.ensure_utc(filters["start_date"])
                )
            if filters.get("end_date"):
                query = query.filter(
                    EventDate.date <= cls.ensure_utc(filters["end_date"])
                )

            # Apply other filters
            if filters.get("city"):
                query = query.filter(Event.city == filters["city"])
            if filters.get("event_type"):
                query = query.filter(Event.event_type == filters["event_type"])
            if filters.get("reservation_status"):
                query = query.filter(
                    Reservation.status == filters["reservation_status"]
                )

            # Region and district filters
            if filters.get("region"):
                query = query.filter(School.region == filters["region"])
            if filters.get("district"):
                query = query.filter(School.district == filters["district"])

            print(f"Final query: {query}")  # Debug print
            reservations = query.all()
            print(f"Number of reservations found: {len(reservations)}")  # Debug print

            reservation_summaries = []
            for reservation in reservations:
                reservation_model = reservation._to_model()
                event_model = reservation.event._to_model()
                event_date_model = reservation.event_date._to_model()
                user_model = reservation.user._to_model()
                school_model = (
                    reservation.user.school._to_model()
                    if reservation.user.school
                    else None
                )

                reservation_summary = {
                    **reservation_model,
                    "event": {
                        "id": event_model["id"],
                        "title": event_model["title"],
                        "institution_name": event_model["institution_name"],
                        "city": event_model["city"],
                        "event_type": event_model["event_type"],
                    },
                    "event_date": {
                        "date": event_date_model["date"],
                        "time": event_date_model["time"],
                        "capacity": event_date_model["capacity"],
                        "available_spots": event_date_model["available_spots"],
                    },
                    "user": {
                        "id": getattr(user_model, "id", None),
                        "name": getattr(user_model, "name", None),
                        "email": getattr(user_model, "email", None),
                    },
                    "school": school_model,
                    "status": reservation.status.value,
                    "cancelled_at": reservation.cancelled_at.isoformat()
                    if reservation.cancelled_at
                    else None,
                }
                reservation_summaries.append(reservation_summary)

            print(
                f"Number of reservation summaries: {len(reservation_summaries)}"
            )  # Debug print
            return reservation_summaries

    @staticmethod
    def ensure_utc(dt):
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def save_report(
        cls, report_data: Dict[str, Any], generated_by: int
    ) -> Dict[str, Any]:
        with get_db_session() as session:
            serialized_filters = json.dumps(
                report_data["filters"], default=cls.serialize_datetime
            )
            serialized_data = json.dumps(
                report_data["data"], default=cls.serialize_datetime
            )
            report = cls(
                report_type=ReportType(report_data["report_type"]),
                generated_by=generated_by,
                filters=serialized_filters,
                data=serialized_data,
            )
            session.add(report)
            session.commit()
            return report._to_model()

    @classmethod
    def delete_report(cls, report_id: int) -> None:
        with get_db_session() as session:
            report = session.query(cls).filter_by(id=report_id).first()
            if report:
                session.delete(report)
                session.commit()
