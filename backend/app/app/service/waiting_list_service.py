import json
import math
from pathlib import Path
import typing
from uuid import uuid4
from app.data_adapter.event import Event, EventDate
from app.models.event import (
    EventCreateModel,
    EventDateModel,
    EventUpdateModel,
    EventModel,
)
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.utils.response_messages import ResponseMessages
from app.logger import logger
from app.context_manager import context_id_api, context_actor_user_data
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.data_adapter.reservation import Reservation
from app.models.waiting_list import (
    WaitingListCreateModel,
    WaitingListModel,
    WaitingListStatus,
    WaitingListUpdateModel,
)
from app.data_adapter.waiting_list import WaitingList
from app.models.reservation import ReservationStatus
from fastapi import status, UploadFile
from datetime import datetime
from pydantic import ValidationError
from typing import Dict, List, Optional, Union


class WaitingListService:
    @staticmethod
    def add_to_waiting_list(
        waiting_list_entry: WaitingListCreateModel,
    ) -> GenericResponseModel:
        print("WaitingListService.add_to_waiting_list", waiting_list_entry)
        try:
            # Check if the event date exists and is not locked
            event_date = EventDate.get_event_date_by_id(
                waiting_list_entry.event_date_id
            )
            if not event_date:
                logger.warning(
                    f"Event date not found. ID: {waiting_list_entry.event_date_id}"
                )
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EVENT_DATE_NOT_FOUND
                )

            if event_date.is_locked():
                logger.warning(
                    f"Event date is locked. ID: {waiting_list_entry.event_date_id}"
                )
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_LOCKED)

            # Create new waiting list entry
            waiting_list_data = waiting_list_entry.dict()
            waiting_list_data["event_id"] = event_date.event_id  # Add the event_id
            new_entry = WaitingList.add_to_waiting_list(waiting_list_data)

            logger.info(f"Added to waiting list successfully. ID: {new_entry.id}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_ADD_TO_WAITING_LIST,
                status_code=status.HTTP_201_CREATED,
                data=WaitingListModel(**new_entry._to_model()),
            )

        except ValidationError as e:
            logger.error(f"Validation error for waiting list entry. Error: {str(e)}")
            raise CustomBadRequestException(
                ResponseMessages.ERR_INVALID_WAITING_LIST_DATA
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(f"Unexpected error adding to waiting list. Error: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def process_waiting_list(event_date_id: int) -> GenericResponseModel:
        try:
            event_date = EventDate.get_event_date_by_id(event_date_id)
            if not event_date:
                logger.warning(f"Event date not found. ID: {event_date_id}")
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EVENT_DATE_NOT_FOUND
                )

            if event_date.is_locked():
                logger.warning(
                    f"Event date is locked. Cannot process waiting list. ID: {event_date_id}"
                )
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_LOCKED)

            waiting_list = WaitingList.get_waiting_list_for_event_date(event_date_id)

            processed_entries = []
            for entry in waiting_list:
                total_requested = entry.number_of_students + entry.number_of_teachers
                if event_date.available_spots >= total_requested:
                    # Create a reservation for this waiting list entry
                    new_reservation = Reservation.create_reservation(
                        {
                            "event_id": event_date.event_id,
                            "event_date_id": event_date_id,
                            "user_id": entry.user_id,
                            "number_of_students": entry.number_of_students,
                            "number_of_teachers": entry.number_of_teachers,
                            "special_requirements": entry.special_requirements,
                            "contact_info": entry.contact_info,
                            "status": ReservationStatus.CONFIRMED,
                        }
                    )

                    if new_reservation:
                        event_date.update_available_spots(
                            event_date_id, -total_requested
                        )
                        WaitingList.update_status(entry.id, WaitingListStatus.PROCESSED)
                        processed_entries.append(entry)
                else:
                    # Stop processing if there are not enough spots for the next entry
                    break

            logger.info(
                f"Processed {len(processed_entries)} waiting list entries for event date ID: {event_date_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_PROCESS_WAITING_LIST,
                status_code=status.HTTP_200_OK,
                data={"processed_entries": len(processed_entries)},
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(f"Unexpected error processing waiting list. Error: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_user_waiting_list_entries(user_id: int) -> GenericResponseModel:
        try:
            # Get all waiting list entries for the user
            waiting_list_entries = WaitingList.get_user_waiting_list_entries(user_id)

            if not waiting_list_entries:
                logger.info(f"No waiting list entries found for user ID: {user_id}")
                return GenericResponseModel(
                    api_id=context_id_api.get(),
                    message=ResponseMessages.MSG_NO_WAITING_LIST_ENTRIES,
                    status_code=status.HTTP_200_OK,
                    data=[],
                )

            # Convert waiting list entries to models
            waiting_list_models = [
                WaitingListModel(**entry._to_model()) for entry in waiting_list_entries
            ]

            logger.info(
                f"Retrieved {len(waiting_list_models)} waiting list entries for user ID: {user_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_USER_WAITING_LIST,
                status_code=status.HTTP_200_OK,
                data=waiting_list_models,
            )

        except Exception as e:
            logger.error(
                f"Unexpected error getting user waiting list entries. User ID: {user_id}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def update_waiting_list_entry(
        waiting_list_id: int, waiting_list_update: WaitingListUpdateModel
    ) -> GenericResponseModel:
        try:
            existing_entry = WaitingList.get_waiting_list_entry_by_id(waiting_list_id)
            if not existing_entry:
                logger.warning(f"Waiting list entry not found. ID: {waiting_list_id}")
                raise CustomBadRequestException(
                    ResponseMessages.ERR_WAITING_LIST_ENTRY_NOT_FOUND
                )

            event_date = EventDate.get_event_date_by_id(existing_entry.event_date_id)
            if not event_date:
                logger.warning(
                    f"Event date not found. ID: {existing_entry.event_date_id}"
                )
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EVENT_DATE_NOT_FOUND
                )

            if event_date.is_locked():
                logger.warning(
                    f"Event date is locked. Cannot update waiting list entry. ID: {waiting_list_id}"
                )
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_LOCKED)

            updated_entry = WaitingList.update_waiting_list_entry(
                waiting_list_id, waiting_list_update.dict()
            )

            logger.info(
                f"Updated waiting list entry successfully. ID: {waiting_list_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_UPDATE_WAITING_LIST_ENTRY,
                status_code=status.HTTP_200_OK,
                data=WaitingListModel(**updated_entry._to_model()),
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(
                f"Unexpected error updating waiting list entry. ID: {waiting_list_id}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def delete_waiting_list_entry(waiting_list_id: int) -> GenericResponseModel:
        try:
            deleted = WaitingList.delete_waiting_list_entry(waiting_list_id)
            if not deleted:
                logger.warning(f"Waiting list entry not found. ID: {waiting_list_id}")
                raise CustomBadRequestException(
                    ResponseMessages.ERR_WAITING_LIST_ENTRY_NOT_FOUND
                )

            logger.info(
                f"Deleted waiting list entry successfully. ID: {waiting_list_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_DELETE_WAITING_LIST_ENTRY,
                status_code=status.HTTP_200_OK,
                data=None,
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(
                f"Unexpected error deleting waiting list entry. ID: {waiting_list_id}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_waiting_list(
        event_date_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Retrieve the waiting list for a specific event date with pagination, filtering, and sorting.

        Args:
            event_date_id (int): The ID of the event date.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            GenericResponseModel: A GenericResponseModel with the paginated list of waiting list entries.
        """
        try:
            waiting_list, total_count = WaitingList.get_waiting_list_for_event_date(
                event_date_id,
                current_page,
                items_per_page,
                filter_params,
                sorting_params,
            )

            total_pages = math.ceil(total_count / items_per_page)

            logger.info(
                f"Waiting list retrieved for event date {event_date_id}. "
                f"Page: {current_page}, Items: {items_per_page}, Total: {total_count}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_WAITING_LIST,
                status_code=status.HTTP_200_OK,
                data=PaginationResponseDataModel(
                    current_page=current_page,
                    items_per_page=items_per_page,
                    total_pages=total_pages,
                    total_items=total_count,
                    items=[
                        WaitingListModel(**entry._to_model()) for entry in waiting_list
                    ],
                ),
            )
        except Exception as e:
            logger.error(f"Error getting waiting list: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_waiting_list_entry_by_event_date_and_user(
        event_date_id: int, user_id: int
    ) -> GenericResponseModel:
        try:
            waiting_list_entry = WaitingList.get_by_event_date_and_user(
                event_date_id, user_id
            )
            if not waiting_list_entry:
                logger.warning(
                    f"Waiting list entry not found for event_date_id: {event_date_id} and user_id: {user_id}"
                )
                raise CustomBadRequestException(
                    ResponseMessages.ERR_WAITING_LIST_ENTRY_NOT_FOUND
                )

            logger.info(
                f"Retrieved waiting list entry successfully for event_date_id: {event_date_id} and user_id: {user_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_WAITING_LIST_ENTRY,
                status_code=status.HTTP_200_OK,
                data=WaitingListModel(**waiting_list_entry._to_model()),
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(
                f"Unexpected error retrieving waiting list entry. event_date_id: {event_date_id}, user_id: {user_id}. Error: {str(e)}"
            )
            raise CustomInternalServerErrorException(
                ResponseMessages.ERR_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def get_waiting_list_entry_by_id(waiting_list_id: int) -> GenericResponseModel:
        try:
            waiting_list_entry = WaitingList.get_by_id(waiting_list_id)
            if not waiting_list_entry:
                logger.warning(f"Waiting list entry not found. ID: {waiting_list_id}")
                raise CustomBadRequestException(
                    ResponseMessages.ERR_WAITING_LIST_ENTRY_NOT_FOUND
                )

            logger.info(
                f"Retrieved waiting list entry successfully. ID: {waiting_list_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_WAITING_LIST_ENTRY,
                status_code=status.HTTP_200_OK,
                data=WaitingListModel(**waiting_list_entry._to_model()),
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(
                f"Unexpected error retrieving waiting list entry. ID: {waiting_list_id}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)
