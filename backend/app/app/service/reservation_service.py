from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.data_adapter.reservation import Reservation
from app.models.reservation import ReservationCreateModel
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.utils.response_messages import ResponseMessages
from app.context_manager import context_id_api, context_actor_user_data
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.logger import logger
from fastapi import status
import math
from app.data_adapter.event import Event


class ReservationService:
    @staticmethod
    def create_reservation(
        session: Session, reservation_data: ReservationCreateModel
    ) -> GenericResponseModel:
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        total_seats = (
            reservation_data.number_of_students + reservation_data.number_of_teachers
        )
        if total_seats <= 0:
            raise CustomBadRequestException(
                ResponseMessages.ERR_INVALID_NUMBER_OF_SEATS
            )

        if reservation_data.user_id != context_actor_user_data.get().user_id:
            raise CustomBadRequestException(ResponseMessages.ERR_INVALID_USER_ID)

        try:
            new_reservation = Reservation.create_reservation(reservation_data)
            logger.info(
                f"User ID {context_actor_user_data.get().user_id} created reservation: {new_reservation['id']}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_CREATE_RESERVATION,
                status_code=status.HTTP_201_CREATED,
                data=new_reservation,
            )
        except CustomBadRequestException as e:
            logger.error(f"Error creating reservation: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating reservation: {str(e)}")
            raise CustomInternalServerErrorException()

    @staticmethod
    def get_reservation_by_id(
        session: Session, reservation_id: int
    ) -> GenericResponseModel:
        """
        Get a reservation by its ID.

        Args:
            session (Session): The database session.
            reservation_id (int): The ID of the reservation to retrieve.

        Returns:
            GenericResponseModel: The response containing the reservation.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        reservation = Reservation.get_reservation_by_id(reservation_id)
        if not reservation:
            logger.error(f"Reservation not found: {reservation_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} retrieved reservation: {reservation_id}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_RESERVATION,
            status_code=status.HTTP_200_OK,
            data=reservation,
        )

    @staticmethod
    def delete_reservation(
        session: Session, reservation_id: int
    ) -> GenericResponseModel:
        """
        Delete a reservation by its ID.

        Args:
            session (Session): The database session.
            reservation_id (int): The ID of the reservation to delete.

        Returns:
            GenericResponseModel: The response confirming the deletion.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        result = Reservation.delete_reservation(reservation_id)
        if not result:
            logger.error(f"Failed to delete reservation: {reservation_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} deleted reservation: {reservation_id}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_DELETE_RESERVATION,
            status_code=status.HTTP_200_OK,
            data=result,
        )

    @staticmethod
    def get_all_reservations(
        session: Session,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Get all reservations with pagination, filtering, and sorting.

        Args:
            session (Session): The database session.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            GenericResponseModel: The response containing the list of reservations and pagination info.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        reservations, total_count = Reservation.get_reservations(
            current_page, items_per_page, filter_params, sorting_params
        )
        total_pages = math.ceil(total_count / items_per_page)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} retrieved all reservations. Page: {current_page}, Items: {items_per_page}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_ALL_RESERVATIONS,
            status_code=status.HTTP_200_OK,
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_count,
                items=reservations,
            ),
        )

    @staticmethod
    def get_reservations_by_event_id(
        session: Session,
        event_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Get all reservations for a specific event with pagination, filtering, and sorting.

        Args:
            session (Session): The database session.
            event_id (int): The ID of the event to get reservations for.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            GenericResponseModel: The response containing the list of reservations and pagination info.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Check if the event exists
        event = session.query(Event).filter_by(id=event_id).first()
        if not event:
            raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

        reservations, total_count = Reservation.get_reservations_by_event_id(
            event_id,
            current_page,
            items_per_page,
            filter_params,
            sorting_params,
        )
        total_pages = math.ceil(total_count / items_per_page)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} retrieved reservations for event ID {event_id}. Page: {current_page}, Items: {items_per_page}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_RESERVATIONS_BY_EVENT,
            status_code=status.HTTP_200_OK,
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_count,
                items=reservations,
            ),
        )

    @staticmethod
    def get_user_reservations(session: Session, user_id: int) -> GenericResponseModel:
        """
        Get all reservations for a specific user.

        This method retrieves all reservations from the database for a given user ID.
        It checks for user authentication and logs the retrieval attempt.

        Args:
            session (Session): The database session.
            user_id (int): The ID of the user to retrieve reservations for.

        Returns:
            GenericResponseModel: The response containing the list of reservations.

        Raises:
            CustomBadRequestException: If the user is not authenticated or not found.
        """
        if not context_actor_user_data.get():
            logger.error("Unauthenticated user attempted to retrieve reservations")
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        try:
            reservations = Reservation.get_reservations_by_user_id(user_id)
            logger.info(f"Retrieved reservations for User ID: {user_id}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_USER_RESERVATIONS,
                status_code=status.HTTP_200_OK,
                data=reservations,
            )
        except Exception as e:
            logger.error(
                f"Error retrieving reservations for User ID {user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def get_reservation_for_user_and_event(
        session: Session, user_id: int, event_id: int
    ) -> GenericResponseModel:
        """
        Get a reservation for a specific user and event.

        This method retrieves a reservation from the database for a given user ID and event ID.
        It checks for user authentication and logs the retrieval attempt.

        Args:
            session (Session): The database session.
            user_id (int): The ID of the user.
            event_id (int): The ID of the event.

        Returns:
            GenericResponseModel: The response containing the reservation data.

        Raises:
            CustomBadRequestException: If the user is not authenticated or the reservation is not found.
        """
        if not context_actor_user_data.get():
            logger.error("Unauthenticated user attempted to retrieve a reservation")
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        try:
            reservation = Reservation.get_reservation_by_user_and_event(
                user_id, event_id
            )
            if not reservation:
                logger.error(
                    f"Reservation not found for User ID: {user_id} and Event ID: {event_id}"
                )
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            logger.info(
                f"Retrieved reservation for User ID: {user_id} and Event ID: {event_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_RESERVATION,
                status_code=status.HTTP_200_OK,
                data=reservation,
            )
        except Exception as e:
            logger.error(
                f"Error retrieving reservation for User ID {user_id} and Event ID {event_id}: {str(e)}"
            )
            raise