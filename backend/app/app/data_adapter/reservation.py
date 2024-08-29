from typing import Dict, Any, List, Optional, Tuple, Union
from app.models.reservation import ReservationStatus, ReservationUpdateModel
from sqlalchemy import Column, Integer, ForeignKey, Text, String, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.context_manager import get_db_session
from app.data_adapter.event import Event
from app.data_adapter.event import EventDate
from app.models.reservation import ReservationCreateModel
from app.utils.exceptions import CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from app.models.get_params import ParameterValidator


class Reservation(Base):
    __tablename__ = "reservation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)
    event_date_id = Column(Integer, ForeignKey("event_date.id"), nullable=False)
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
    local_reservation_code = Column(String(20), nullable=False, unique=True)
    cancelled_at = Column(DateTime, nullable=True)

    event = relationship("Event", back_populates="reservations")
    event_date = relationship("EventDate", back_populates="reservations")
    user = relationship("User", back_populates="reservations")

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the Reservation object to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the Reservation.
        """
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_date_id": self.event_date_id,
            "user_id": self.user_id,
            "number_of_students": self.number_of_students,
            "number_of_teachers": self.number_of_teachers,
            "special_requirements": self.special_requirements,
            "contact_info": self.contact_info,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "local_reservation_code": self.local_reservation_code,
        }

    @classmethod
    def create_reservation(
        cls, reservation_data: ReservationCreateModel
    ) -> Dict[str, Any]:
        """
        Create a new reservation for an event.

        Args:
            reservation_data (ReservationCreateModel): The data for creating the reservation.

        Returns:
            Dict[str, Any]: A dictionary representation of the created Reservation.

        Raises:
            CustomBadRequestException: If the event or event date is not found, or if there's insufficient capacity.
        """
        with get_db_session() as session:
            # Check if the event exists
            event = session.query(Event).filter_by(id=reservation_data.event_id).first()
            if not event:
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

            # Check if the event date exists and belongs to the event
            event_date = (
                session.query(EventDate)
                .filter_by(
                    id=reservation_data.event_date_id,
                    event_id=reservation_data.event_id,
                )
                .first()
            )
            if not event_date:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EVENT_DATE_NOT_FOUND
                )

            # Calculate total seats and check if booking is possible
            total_seats = (
                reservation_data.number_of_students
                + reservation_data.number_of_teachers
            )
            if event_date.book_seats(total_seats):
                # Create new reservation
                new_reservation = cls(
                    event_id=reservation_data.event_id,
                    event_date_id=reservation_data.event_date_id,
                    user_id=reservation_data.user_id,
                    number_of_students=reservation_data.number_of_students,
                    number_of_teachers=reservation_data.number_of_teachers,
                    special_requirements=reservation_data.special_requirements,
                    contact_info=reservation_data.contact_info,
                    status=ReservationStatus.PENDING,
                    local_reservation_code=cls.generate_local_code(session),
                )
                session.add(new_reservation)
                session.commit()
                return new_reservation._to_model()
            else:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_INSUFFICIENT_CAPACITY
                )

    @classmethod
    def update_reservation(
        cls, reservation_id: int, reservation_data: ReservationUpdateModel
    ) -> Dict[str, Any]:
        """
        Update an existing reservation in the database.

        This method updates a reservation with the given ID using the provided data.
        It checks for capacity changes and updates event dates accordingly.

        Args:
            reservation_id (int): The ID of the reservation to update.
            reservation_data (ReservationUpdateModel): A Pydantic model containing the fields to update.

        Returns:
            Dict[str, Any]: A dictionary representation of the updated reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found, event date is invalid,
                                       or there's insufficient capacity.

        Note:
            This method uses SQLAlchemy's ORM to update the reservation object.
            It handles capacity changes and updates related event dates.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            # Check if the event date exists and belongs to the event
            new_event_date = (
                session.query(EventDate)
                .filter_by(
                    id=reservation_data.event_date_id,
                    event_id=reservation_data.event_id,
                )
                .first()
            )
            if not new_event_date:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EVENT_DATE_NOT_FOUND
                )

            old_event_date = (
                session.query(EventDate).filter_by(id=reservation.event_date_id).first()
            )

            # Calculate the change in seats
            old_total_seats = (
                reservation.number_of_students + reservation.number_of_teachers
            )
            new_total_seats = (
                reservation_data.number_of_students
                + reservation_data.number_of_teachers
            )

            # Handle capacity changes
            if reservation.event_date_id != reservation_data.event_date_id:
                if not new_event_date.book_seats(new_total_seats):
                    raise CustomBadRequestException(
                        ResponseMessages.ERR_INSUFFICIENT_CAPACITY
                    )
                old_event_date.available_spots += old_total_seats
            else:
                seats_difference = new_total_seats - old_total_seats
                if seats_difference > 0 and not new_event_date.book_seats(
                    seats_difference
                ):
                    raise CustomBadRequestException(
                        ResponseMessages.ERR_INSUFFICIENT_CAPACITY
                    )
                elif seats_difference < 0:
                    new_event_date.available_spots -= seats_difference

            # Update the reservation object with the new data
            for key, value in reservation_data.dict(exclude_unset=True).items():
                setattr(reservation, key, value)

            session.commit()
            session.refresh(reservation)

            return reservation._to_model()

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
        Cancel a reservation by changing its status to CANCELLED.

        Args:
            reservation_id (int): The ID of the reservation to cancel.

        Returns:
            Dict[str, Any]: A dictionary containing the updated reservation details.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            # Check if the reservation is already cancelled
            if reservation.status == ReservationStatus.CANCELLED:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_ALREADY_CANCELLED
                )

            # Update available spots for the event date
            event_date = (
                session.query(EventDate).filter_by(id=reservation.event_date_id).first()
            )
            if event_date:
                event_date.available_spots += (
                    reservation.number_of_students + reservation.number_of_teachers
                )

            # Change the reservation status to CANCELLED
            reservation.status = ReservationStatus.CANCELLED

            # Add a timestamp for when the reservation was cancelled
            reservation.cancelled_at = datetime.utcnow()

            session.commit()
            return reservation._to_model()

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

    @staticmethod
    def generate_local_code(session) -> str:
        """
        Generate a unique local reservation code.

        Args:
            session: The database session.

        Returns:
            str: A unique local reservation code.
        """
        import random
        import string

        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if (
                not session.query(Reservation)
                .filter_by(local_reservation_code=code)
                .first()
            ):
                return code

    @classmethod
    def cancel_reservation(cls, reservation_id: int) -> Dict[str, Any]:
        """
        Cancel a reservation by its ID.

        Args:
            reservation_id (int): The ID of the reservation to cancel.

        Returns:
            Dict[str, Any]: A dictionary representation of the cancelled Reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            # Update available spots for the event date
            event_date = (
                session.query(EventDate).filter_by(id=reservation.event_date_id).first()
            )
            if event_date:
                event_date.available_spots += (
                    reservation.number_of_students + reservation.number_of_teachers
                )

            reservation.status = ReservationStatus.CANCELLED

            session.commit()
            session.refresh(reservation)

            return reservation._to_model()

    @classmethod
    def get_reservations_for_user_and_event(
        cls, user_id: int, event_id: int, page: int = 1, items_per_page: int = 100
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve paginated reservations for a specific user and event from the database.

        Args:
            user_id (int): The ID of the user.
            event_id (int): The ID of the event.
            page (int): The current page number (default: 1).
            items_per_page (int): The number of items per page (default: 10).

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing a list of dictionaries with reservation data and the total count of reservations.

        Raises:
            CustomBadRequestException: If an error occurs during the database query.
        """
        try:
            with get_db_session() as session:
                query = session.query(cls).filter(
                    cls.user_id == user_id, cls.event_id == event_id
                )

                total_count = query.count()

                reservations = (
                    query.offset((page - 1) * items_per_page)
                    .limit(items_per_page)
                    .all()
                )

                return [
                    reservation._to_model() for reservation in reservations
                ], total_count
        except Exception as e:
            # Log the error here
            raise CustomBadRequestException(f"Error retrieving reservations: {str(e)}")

    @classmethod
    def find_by_code(cls, reservation_code: str) -> Optional[Dict[str, Any]]:
        """
        Find a reservation by its local reservation code.

        Args:
            reservation_code (str): The local reservation code to search for.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the reservation details,
                                      or None if no reservation is found.
        """
        with get_db_session() as session:
            reservation = (
                session.query(cls)
                .filter(cls.local_reservation_code == reservation_code)
                .first()
            )
            if reservation:
                return reservation._to_model()
            return None

    @classmethod
    def confirm_reservation(cls, reservation_id: int) -> Dict[str, Any]:
        """
        Confirm a reservation by its ID.

        Args:
            reservation_id (int): The ID of the reservation to confirm.

        Returns:
            Dict[str, Any]: A dictionary representation of the confirmed Reservation.

        Raises:
            CustomBadRequestException: If the reservation is not found.
        """
        with get_db_session() as session:
            reservation = session.query(cls).filter_by(id=reservation_id).first()
            if not reservation:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            reservation.status = ReservationStatus.CONFIRMED

            session.commit()
            session.refresh(reservation)

            return reservation._to_model()
