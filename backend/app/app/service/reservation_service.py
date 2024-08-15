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
        """
        Create a new reservation.

        Args:
            session (Session): The database session.
            reservation_data (ReservationCreateModel): The data for the new reservation.

        Returns:
            GenericResponseModel: The response containing the created reservation.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        if reservation_data.number_of_seats <= 0:
            raise CustomBadRequestException(
                ResponseMessages.ERR_INVALID_NUMBER_OF_SEATS
            )

        # Check if the user ID in the reservation data matches the authenticated user
        if reservation_data.user_id != context_actor_user_data.get().user_id:
            raise CustomBadRequestException(ResponseMessages.ERR_INVALID_USER_ID)

        try:
            new_reservation = Reservation.create_reservation(session, reservation_data)
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
            logger.error(
                f"Error creating reservation for User ID {context_actor_user_data.get().user_id}: {str(e)}"
            )
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

        reservation = Reservation.get_reservation_by_id(session, reservation_id)
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

        result = Reservation.delete_reservation(session, reservation_id)
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
            session, current_page, items_per_page, filter_params, sorting_params
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
            session,
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
