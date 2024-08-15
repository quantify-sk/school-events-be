from app.models.get_params import ParameterValidator
from sqlalchemy import Column, Integer, Enum, ForeignKey
from sqlalchemy.orm import Session
from app.database import Base
from app.models.reservation import ReservationStatus, ReservationCreateModel
from app.data_adapter.event import Event
from app.utils.exceptions import CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from typing import List, Optional, Tuple, Dict, Any, Union


class Reservation(Base):
    __tablename__ = "reservation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    number_of_seats = Column(Integer, nullable=False)
    status = Column(
        Enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING
    )

    def __init__(self, event_id: int, user_id: int, number_of_seats: int, status: str):
        self.event_id = event_id
        self.user_id = user_id
        self.number_of_seats = number_of_seats
        self.status = status

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the Reservation object to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the Reservation.
        """
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "number_of_seats": self.number_of_seats,
            "status": self.status,
        }

    @classmethod
    def create_reservation(
        cls, session: Session, reservation_data: ReservationCreateModel
    ) -> Dict[str, Any]:
        """
        Create a new reservation.

        Args:
            session (Session): The database session.
            reservation_data (ReservationCreateModel): The data for the new reservation.

        Returns:
            Dict[str, Any]: The created reservation as a dictionary.

        Raises:
            CustomBadRequestException: If the event is not found or there's not enough capacity.
        """
        event = session.query(Event).filter_by(id=reservation_data.event_id).first()
        if not event:
            raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

        # Check current reservations for this event
        current_reservations = (
            session.query(cls)
            .filter_by(event_id=event.id, status=ReservationStatus.CONFIRMED)
            .all()
        )
        total_reserved_seats = sum(
            reservation.number_of_seats for reservation in current_reservations
        )

        if event.capacity < total_reserved_seats + reservation_data.number_of_seats:
            raise CustomBadRequestException(ResponseMessages.ERR_INSUFFICIENT_CAPACITY)

        new_reservation = cls(
            event_id=reservation_data.event_id,
            user_id=reservation_data.user_id,
            number_of_seats=reservation_data.number_of_seats,
            status=ReservationStatus.CREATED,  # Assuming we're creating confirmed reservations
        )
        session.add(new_reservation)
        session.commit()
        return new_reservation._to_model()

    @classmethod
    def get_reservation_by_id(
        cls, session: Session, reservation_id: int
    ) -> Dict[str, Any]:
        """
        Get a reservation by its ID.

        Args:
            session (Session): The database session.
            reservation_id (int): The ID of the reservation to retrieve.

        Returns:
            Dict[str, Any]: The reservation as a dictionary.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        reservation = session.query(cls).filter_by(id=reservation_id).first()
        if not reservation:
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        return reservation._to_model()

    @classmethod
    def delete_reservation(
        cls, session: Session, reservation_id: int
    ) -> Dict[str, int]:
        """
        Delete a reservation by its ID.

        Args:
            session (Session): The database session.
            reservation_id (int): The ID of the reservation to delete.

        Returns:
            Dict[str, int]: A dictionary containing the ID of the deleted reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        reservation = session.query(cls).filter_by(id=reservation_id).first()
        if not reservation:
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        session.delete(reservation)
        session.commit()
        return {"reservation_id": reservation_id}

    @classmethod
    def get_reservations(
        cls,
        session: Session,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = session.query(cls)

        # Apply filters and sorting
        query = ParameterValidator.apply_filters_and_sorting(
            query,
            cls,
            filter_params,
            sorting_params,
        )

        total_count = query.count()
        reservations = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [reservation._to_model() for reservation in reservations], total_count

    @classmethod
    def get_reservations_by_event_id(
        cls,
        session: Session,
        event_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = session.query(cls).filter(cls.event_id == event_id)

        # Apply filters and sorting
        query = ParameterValidator.apply_filters_and_sorting(
            query,
            cls,
            filter_params,
            sorting_params,
        )

        total_count = query.count()
        reservations = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [reservation._to_model() for reservation in reservations], total_count
