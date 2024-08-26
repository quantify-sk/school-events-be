from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, JSON, and_
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.context_manager import get_db_session
from app.database import Base
from enum import Enum as PyEnum
from typing import List, Dict, Any
from app.utils.exceptions import CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from app.data_adapter.event import Event, EventDate
from app.data_adapter.reservation import Reservation
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
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    @classmethod
    def create_report(cls, report_type: ReportType, generated_by: int, filters: dict, data: dict) -> Dict[str, Any]:
        with get_db_session() as session:
            serialized_filters = json.dumps(filters, default=cls.serialize_datetime)
            serialized_data = json.dumps(data, default=cls.serialize_datetime)
            report = cls(report_type=report_type, generated_by=generated_by, filters=serialized_filters, data=serialized_data)
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
    def generate_event_summary(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            query = session.query(Event).join(EventDate)

            date_filter = []
            if filters.get('start_date'):
                start_date = cls.ensure_utc(filters['start_date'])
                date_filter.append(EventDate.date >= start_date)
            if filters.get('end_date'):
                end_date = cls.ensure_utc(filters['end_date'])
                date_filter.append(EventDate.date <= end_date)

            if date_filter:
                query = query.filter(and_(*date_filter))

            # Add any other filters you might need
            if filters.get('city'):
                query = query.filter(Event.city == filters['city'])
            if filters.get('event_type'):
                query = query.filter(Event.event_type == filters['event_type'])

            # Use distinct to avoid duplicate events
            events = query.distinct().all()

            event_summaries = []
            for event in events:
                event_model = event._to_model()
                # Filter event dates based on the date range
                filtered_dates = [
                    date for date in event_model['event_dates']
                    if (not filters.get('start_date') or cls.ensure_utc(date['date']) >= start_date) and
                       (not filters.get('end_date') or cls.ensure_utc(date['date']) <= end_date)
                ]
                event_model['event_dates'] = filtered_dates
                event_summaries.append(event_model)

            return event_summaries

    @staticmethod
    def ensure_utc(dt):
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)



    @classmethod
    def generate_attendance_report(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            query = session.query(Reservation).join(EventDate).join(Event)
            if filters.get('start_date'):
                query = query.filter(EventDate.date >= filters['start_date'])
            if filters.get('end_date'):
                query = query.filter(EventDate.date <= filters['end_date'])
            reservations = query.all()
            return [reservation._to_model() for reservation in reservations]
        
    @classmethod
    def generate_reservation_report(cls, filters: dict) -> List[Dict[str, Any]]:
        with get_db_session() as session:
            query = session.query(Reservation).join(EventDate).join(Event).join(Reservation.user)

            date_filter = []
            if filters.get('start_date'):
                start_date = cls.ensure_utc(filters['start_date'])
                date_filter.append(EventDate.date >= start_date)
            if filters.get('end_date'):
                end_date = cls.ensure_utc(filters['end_date'])
                date_filter.append(EventDate.date <= end_date)

            if date_filter:
                query = query.filter(and_(*date_filter))

            # Add any other filters you might need
            if filters.get('city'):
                query = query.filter(Event.city == filters['city'])
            if filters.get('event_type'):
                query = query.filter(Event.event_type == filters['event_type'])
            if filters.get('status'):
                query = query.filter(Reservation.status == ReservationStatus(filters['status']))

            reservations = query.all()

            reservation_summaries = []
            for reservation in reservations:
                reservation_model = reservation._to_model()
                event_model = reservation.event._to_model()
                event_date_model = reservation.event_date._to_model()
                user_model = reservation.user._to_model()

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
                        "id": getattr(user_model, 'id', None),
                        "name": getattr(user_model, 'name', None),
                        "email": getattr(user_model, 'email', None),
                    },
                    "status": reservation.status.value,
                    "cancelled_at": reservation.cancelled_at.isoformat() if reservation.cancelled_at else None,
                }
                reservation_summaries.append(reservation_summary)

            return reservation_summaries