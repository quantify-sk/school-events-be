from app.models.get_params import ParameterValidator
from sqlalchemy import Column, Integer, Enum, ForeignKey, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.reservation import ReservationStatus, ReservationCreateModel
from app.utils.exceptions import CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from app.context_manager import get_db_session
from typing import List, Optional, Tuple, Dict, Any, Union

# Assuming Event is imported here, or you can import it directly.
from app.data_adapter.event import Event


class Reservation(Base):
    __tablename__ = "reservation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    number_of_students = Column(Integer, nullable=False)
    number_of_teachers = Column(Integer, nullable=False)
    special_requirements = Column(Text, nullable=True)
    contact_info = Column(String(255), nullable=False)
    status = Column(
        Enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(
        self,
        event_id: int,
        user_id: int,
        number_of_students: int,
        number_of_teachers: int,
        special_requirements: str,
        contact_info: str,
        status: ReservationStatus = ReservationStatus.PENDING,
    ):
        self.event_id = event_id
        self.user_id = user_id
        self.number_of_students = number_of_students
        self.number_of_teachers = number_of_teachers
        self.special_requirements = special_requirements
        self.contact_info = contact_info
        self.status = status

    def _to_model(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "number_of_students": self.number_of_students,
            "number_of_teachers": self.number_of_teachers,
            "special_requirements": self.special_requirements,
            "contact_info": self.contact_info,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def create_reservation(
        cls, reservation_data: ReservationCreateModel
    ) -> Dict[str, Any]:
        """
        Create a new reservation for an event.

        This method creates a new reservation based on the provided data. It checks if the event exists
        and if there's sufficient capacity before creating the reservation.

        Args:
            reservation_data (ReservationCreateModel): The data for the new reservation.

        Returns:
            Dict[str, Any]: A dictionary representation of the created reservation.

        Raises:
            CustomBadRequestException: If the event is not found or there's insufficient capacity.
        """
        with get_db_session() as session:
            # Check if the event exists
            event = session.query(Event).filter_by(id=reservation_data.event_id).first()
            if not event:
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

            # Calculate total seats and check if booking is possible
            total_seats = (
                reservation_data.number_of_students
                + reservation_data.number_of_teachers
            )
            if event.book_seats(total_seats):
                # Create new reservation
                new_reservation = cls(
                    event_id=reservation_data.event_id,
                    user_id=reservation_data.user_id,
                    number_of_students=reservation_data.number_of_students,
                    number_of_teachers=reservation_data.number_of_teachers,
                    special_requirements=reservation_data.special_requirements,
                    contact_info=reservation_data.contact_info,
                    status=ReservationStatus.CONFIRMED,
                )
                session.add(new_reservation)
                session.commit()
                return new_reservation._to_model()
            else:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_INSUFFICIENT_CAPACITY
                )

    @classmethod
    def get_reservation_by_id(cls, reservation_id: int) -> Dict[str, Any]:
        """
        Retrieve a reservation by its ID.

        Args:
            reservation_id (int): The ID of the reservation to retrieve.

        Returns:
            Dict[str, Any]: A dictionary representation of the reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )
            return reservation._to_model()

    @classmethod
    def delete_reservation(cls, reservation_id: int) -> Dict[str, int]:
        """
        Delete a reservation by its ID.

        Args:
            reservation_id (int): The ID of the reservation to delete.

        Returns:
            Dict[str, int]: A dictionary containing the ID of the deleted reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            # Retrieve the event associated with this reservation to update available spots
            event = session.query(Event).filter_by(id=reservation.event_id).first()
            if event:
                event.available_spots += (
                    reservation.number_of_students + reservation.number_of_teachers
                )
                session.add(event)

            session.delete(reservation)
            session.commit()
            return {"reservation_id": reservation_id}

    @classmethod
    def get_reservations(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve a paginated list of reservations with optional filtering and sorting.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): Parameters for filtering the reservations.
            sorting_params (Optional[List[Dict[str, str]]]): Parameters for sorting the reservations.

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing a list of reservation dictionaries and the total count.
        """
        with get_db_session() as session:
            query = session.query(cls)

            # Apply filters and sorting
            query = ParameterValidator.apply_filters_and_sorting(
                query, cls, filter_params, sorting_params
            )

            total_count = query.count()

            reservations = (
                query.offset((current_page - 1) * items_per_page)
                .limit(items_per_page)
                .all()
            )

            return [
                reservation._to_model() for reservation in reservations
            ], total_count

    @classmethod
    def get_reservations_by_event_id(
        cls,
        event_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve a paginated list of reservations for a specific event with optional filtering and sorting.

        Args:
            event_id (int): The ID of the event to get reservations for.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): Parameters for filtering the reservations.
            sorting_params (Optional[List[Dict[str, str]]]): Parameters for sorting the reservations.

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing a list of reservation dictionaries and the total count.
        """
        with get_db_session() as session:
            query = session.query(cls).filter(cls.event_id == event_id)

            query = ParameterValidator.apply_filters_and_sorting(
                query, cls, filter_params, sorting_params
            )

            total_count = query.count()

            reservations = (
                query.offset((current_page - 1) * items_per_page)
                .limit(items_per_page)
                .all()
            )

            return [
                reservation._to_model() for reservation in reservations
            ], total_count

    @classmethod
    def get_reservations_by_user_id(cls, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all reservations for a specific user from the database.

        Args:
            user_id (int): The ID of the user to retrieve reservations for.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing the reservation data.
        """
        with get_db_session() as session:
            reservations = session.query(cls).filter_by(user_id=user_id).all()
            return [reservation._to_model() for reservation in reservations]

    @classmethod
    def get_reservation_by_user_and_event(
        cls, user_id: int, event_id: int
    ) -> Dict[str, Any]:
        """
        Retrieve a reservation for a specific user and event from the database.

        Args:
            user_id (int): The ID of the user.
            event_id (int): The ID of the event.

        Returns:
            Dict[str, Any]: A dictionary containing the reservation data.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = (
                session.query(cls).filter_by(user_id=user_id, event_id=event_id).first()
            )
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )
            return reservation._to_model()
