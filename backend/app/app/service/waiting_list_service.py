import json
import math
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Union
from uuid import uuid4
from app.data_adapter.event import Event, EventDate
from app.models.event import EventCreateModel, EventDateModel, EventUpdateModel, EventModel
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.utils.response_messages import ResponseMessages
from app.logger import logger
from app.context_manager import context_id_api, context_actor_user_data
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.data_adapter.reservation import Reservation
from app.models.waiting_list import WaitingListCreateModel, WaitingListModel, WaitingListStatus
from app.data_adapter.waiting_list import WaitingList
from app.models.reservation import ReservationStatus
from fastapi import status, UploadFile
from datetime import datetime
from pydantic import ValidationError


class WaitingListService:
    @staticmethod
    def add_to_waiting_list(waiting_list_entry: WaitingListCreateModel) -> GenericResponseModel:
        try:
            # Check if the event date exists and is not locked
            event_date = EventDate.get_event_date_by_id(waiting_list_entry.event_date_id)
            if not event_date:
                logger.warning(f"Event date not found. ID: {waiting_list_entry.event_date_id}")
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_NOT_FOUND)

            current_time = datetime.utcnow()
            if current_time >= event_date.lock_time:
                logger.warning(f"Event date is locked. ID: {waiting_list_entry.event_date_id}")
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_LOCKED)

            # Create new waiting list entry
            new_entry = WaitingList.add_to_waiting_list(waiting_list_entry.dict())

            logger.info(f"Added to waiting list successfully. ID: {new_entry.id}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_ADD_TO_WAITING_LIST,
                status_code=status.HTTP_201_CREATED,
                data=WaitingListModel(**new_entry._to_model()),
            )

        except ValidationError as e:
            logger.error(f"Validation error for waiting list entry. Error: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INVALID_WAITING_LIST_DATA)

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
                raise CustomBadRequestException(ResponseMessages.ERR_EVENT_DATE_NOT_FOUND)

            waiting_list = WaitingList.get_waiting_list_for_event_date(event_date_id)

            processed_entries = []
            for entry in waiting_list:
                total_requested = entry.number_of_students + entry.number_of_teachers
                if event_date.available_spots >= total_requested:
                    # Create a reservation for this waiting list entry
                    new_reservation = Reservation.create_reservation({
                        "event_id": event_date.event_id,
                        "event_date_id": event_date_id,
                        "user_id": entry.user_id,
                        "number_of_students": entry.number_of_students,
                        "number_of_teachers": entry.number_of_teachers,
                        "special_requirements": entry.special_requirements,
                        "contact_info": entry.contact_info,
                        "status": ReservationStatus.CONFIRMED
                    })
                    
                    if new_reservation:
                        event_date.update_available_spots(event_date_id, -total_requested)
                        WaitingList.update_status(entry.id, WaitingListStatus.PROCESSED)
                        processed_entries.append(entry)
                else:
                    # Stop processing if there are not enough spots for the next entry
                    break

            logger.info(f"Processed {len(processed_entries)} waiting list entries for event date ID: {event_date_id}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_PROCESS_WAITING_LIST,
                status_code=status.HTTP_200_OK,
                data={"processed_entries": len(processed_entries)}
            )

        except CustomBadRequestException as e:
            raise e

        except Exception as e:
            logger.error(f"Unexpected error processing waiting list. Error: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)