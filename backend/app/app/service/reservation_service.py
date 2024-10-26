from pathlib import Path
import app.api.v1.endpoints
from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.data_adapter.reservation import Reservation
from app.models.reservation import ReservationCreateModel, ReservationUpdateModel
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.utils.response_messages import ResponseMessages
from app.context_manager import context_id_api, context_actor_user_data
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.logger import logger
from fastapi import status, BackgroundTasks
import math
from app.data_adapter.event import Event
from io import BytesIO
import os
import qrcode
from PIL import Image
import os
import json

from app.data_adapter.email_log import EmailLog, EmailLogStatus
from app.models.email_log import EmailLogTemplates, EmailLogTypes, EmailLogLanguage
from app.service.email_service import EmailService
from app.data_adapter.user import User

class ReservationService:

    @staticmethod
    def create_reservation(
        session: Session, reservation_data: ReservationCreateModel, background_tasks: BackgroundTasks
    ) -> GenericResponseModel:
        qr_code_dir = "/code/app/qr_codes"
        qr_code_path = None

        try:
            # Ensure directory exists
            os.makedirs(qr_code_dir, exist_ok=True)

            # Create the reservation
            new_reservation = Reservation.create_reservation(reservation_data)

            # Generate QR code
            local_reservation_code = new_reservation['local_reservation_code']
            qr_code_filename = f"qr_code_{local_reservation_code}.png"
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename)

            # Generate QR code
            logger.info(f"Generating QR code at path: {qr_code_path}")
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(local_reservation_code)
            qr.make(fit=True)

            # Create and save the image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_image.save(qr_code_path)

            if os.path.exists(qr_code_path):
                file_size = os.path.getsize(qr_code_path)
                logger.info(f"QR code created successfully. Size: {file_size} bytes")

                # Create email log entry
                email_data = {
                    'reservation_code': local_reservation_code,
                    'event_name': new_reservation.get('event_title'),
                    'event_date': new_reservation.get('event_date_date').strftime('%Y-%m-%d'),
                    'qr_code_path': qr_code_path,
                }

                user = User.get_user_by_id(new_reservation.get('user_id'))

                email_log = EmailLog.create_new_email_log(
                    user_id=context_actor_user_data.get().user_id,
                    recipient_email=user.user_email,
                    subject="Your Reservation Confirmation",
                    email_data=json.dumps(email_data),
                    email_template=EmailLogTemplates.SCHOOL_REPRESENTATIVE_RESERVATION,
                    email_type=EmailLogTypes.SCHOOL_REPRESENTATIVE_RESERVATION,
                    language=EmailLogLanguage.SK,
                )

                # Send email with QR code attachment
                logger.info(f"Sending email with verified attachment: {qr_code_path}")
                background_tasks.add_task(
                    EmailService.send_new_email,
                    email_log,
                    [qr_code_path]  # Pass the path to be cleaned up after email is sent
                )

            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_CREATE_RESERVATION,
                status_code=status.HTTP_201_CREATED,
                data=new_reservation,
            )

        except Exception as e:
            logger.error(f"Error in create_reservation: {str(e)}")
            # Only clean up QR code if there's an error
            if qr_code_path and os.path.exists(qr_code_path):
                try:
                    os.remove(qr_code_path)
                    logger.info(f"Cleaned up QR code file after error: {qr_code_path}")
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up QR code file: {cleanup_error}")
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
            logger.error(f"Reservation not found: {reservation_id} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        logger.info(
            f"user_id={context_actor_user_data.get().user_id} retrieved reservation: {reservation_id}"
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
            logger.error(f"Failed to delete reservation: {reservation_id} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

        logger.info(
            f"user_id={context_actor_user_data.get().user_id} deleted reservation: {reservation_id}"
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
            f"user_id={context_actor_user_data.get().user_id} retrieved all reservations. Page: {current_page}, Items: {items_per_page}"
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
            f"user_id={context_actor_user_data.get().user_id} retrieved reservations for event ID {event_id}. Page: {current_page}, Items: {items_per_page}"
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
                f"Error retrieving reservations for User ID {user_id}: {str(e)} user_id={context_actor_user_data.get().user_id}"
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
                    f"Reservation not found for user_id={context_actor_user_data.get().user_id} and Event ID: {event_id}"
                )
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )

            logger.info(
                f"Retrieved reservation for user_id={context_actor_user_data.get().user_id} and Event ID: {event_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_RESERVATION,
                status_code=status.HTTP_200_OK,
                data=reservation,
            )
        except Exception as e:
            logger.error(
                f"Error retrieving reservation for user_id={context_actor_user_data.get().user_id} and Event ID {event_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_reservation(
        db: Session, reservation_id: int, reservation_data: ReservationUpdateModel
    ) -> GenericResponseModel:
        """
        Update an existing reservation in the database.

        This static method serves as a wrapper for the class method update_reservation.
        It calls the class method with the provided parameters and wraps the result in a GenericResponseModel.

        Args:
            db (Session): The database session.
            reservation_id (int): The ID of the reservation to update.
            reservation_data (ReservationUpdateModel): A Pydantic model containing the fields to update.

        Returns:
            GenericResponseModel: A generic response model containing the updated reservation data.

        Raises:
            CustomBadRequestException: If the reservation with the given ID is not found or if there's insufficient capacity.

        Note:
            This method delegates the actual update operation to the class method.
        """
        try:
            # Call the class method to update the reservation
            updated_reservation = Reservation.update_reservation(
                reservation_id, reservation_data
            )

            # Wrap the updated reservation in a GenericResponseModel
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_UPDATE_RESERVATION,
                status_code=status.HTTP_200_OK,
                data=updated_reservation,
            )
        except CustomBadRequestException as e:
            # Re-raise the exception to be handled by the caller
            raise e
        except Exception as e:
            # Log the unexpected error and raise a generic exception
            logger.error(f"Unexpected error updating reservation: {str(e)} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_reservations_for_user_and_event(
        user_id: int,
        event_id: int,
        current_page: int = 1,
        items_per_page: int = 10,
        filter_params: Optional[Dict[str, Union[str, List[str]]]] = None,
        sorting_params: Optional[List[Dict[str, str]]] = None,
    ) -> GenericResponseModel:
        """
        Retrieve paginated reservations for a specific user and event.

        Args:
            user_id (int): The ID of the user.
            event_id (int): The ID of the event.
            current_page (int): The current page number (default: 1).
            items_per_page (int): The number of items per page (default: 10).
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            GenericResponseModel: A GenericResponseModel with the list of reservations and pagination info.

        Raises:
            CustomBadRequestException: If there's an error retrieving the reservations.
        """
        try:
            reservations, total_count = Reservation.get_reservations_for_user_and_event(
                user_id,
                event_id,
                current_page,
                items_per_page,
                filter_params,
                sorting_params,
            )
            total_pages = math.ceil(total_count / items_per_page)

            logger.info(
                f"User reservations retrieved. user_id={context_actor_user_data.get().user_id}, Event ID: {event_id}, "
                f"Page: {current_page}, Items: {items_per_page}, Total: {total_count}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_USER_EVENT_RESERVATIONS,
                status_code=status.HTTP_200_OK,
                data=PaginationResponseDataModel(
                    current_page=current_page,
                    items_per_page=items_per_page,
                    total_pages=total_pages,
                    total_items=total_count,
                    items=reservations,
                ),
            )
        except Exception as e:
            logger.error(f"Error retrieving reservations: {str(e)} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(f"Error retrieving reservations: {str(e)}")

    @staticmethod
    def find_reservation_by_code(reservation_code: str) -> GenericResponseModel:
        """
        Find a reservation by its local reservation code.

        Args:
            reservation_code (str): The local reservation code to search for.

        Returns:
            GenericResponseModel: A response model containing the reservation details.
        """
        try:
            reservation = Reservation.find_by_code(reservation_code)

            if reservation:
                return GenericResponseModel(
                    api_id=context_id_api.get(),
                    message=ResponseMessages.MSG_SUCCESS_FIND_RESERVATION,
                    status_code=status.HTTP_200_OK,
                    data=reservation,
                )
            else:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_RESERVATION_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error finding reservation: {str(e)} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_RESERVATION_NOT_FOUND)

    @staticmethod
    def confirm_reservation(reservation_id: int) -> GenericResponseModel:
        """
        Confirm a reservation by setting its status to 'confirmed'.

        Args:
            reservation_id (int): The ID of the reservation to confirm.

        Returns:
            GenericResponseModel: A response model containing the updated reservation details.
        """
        try:
            updated_reservation = Reservation.confirm_reservation(reservation_id)

            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_CONFIRM_RESERVATION,
                status_code=status.HTTP_200_OK,
                data=updated_reservation,
            )
        except CustomBadRequestException as e:
            raise e
        except Exception as e:
            logger.error(f"Error confirming reservation: {str(e)} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)
        
    @staticmethod
    def reject_reservation(reservation_id: int) -> GenericResponseModel:
        """
        Reject a reservation by setting its status to 'rejected'.

        Args:
            reservation_id (int): The ID of the reservation to reject.

        Returns:
            GenericResponseModel: A response model containing the updated reservation details.
        """
        try:
            updated_reservation = Reservation.reject_reservation(reservation_id)

            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_REJECT_RESERVATION,
                status_code=status.HTTP_200_OK,
                data=updated_reservation,
            )
        except CustomBadRequestException as e:
            raise e
        except Exception as e:
            logger.error(f"Error rejecting reservation: {str(e)} user_id={context_actor_user_data.get().user_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)
