import json
import math
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Union
from uuid import uuid4
from app.data_adapter.event import Event
from app.models.event import EventCreateModel, EventUpdateModel, EventModel
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.utils.response_messages import ResponseMessages
from app.logger import logger
from app.context_manager import context_id_api, context_actor_user_data
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from fastapi import status, UploadFile
from datetime import datetime


class EventService:
    @staticmethod
    async def handle_attachments(attachments: List[UploadFile]) -> List[Dict[str, str]]:
        """
        Handle file attachments by saving them and returning their information.

        Args:
            attachments (List[UploadFile]): List of file attachments.

        Returns:
            List[Dict[str, str]]: List of dictionaries containing attachment information.
        """
        attachment_info = []
        uploads_dir = Path("uploads")
        uploads_dir.mkdir(exist_ok=True)

        for attachment in attachments:
            file_name = f"{uuid4()}_{attachment.filename}"
            file_location = uploads_dir / file_name

            with open(file_location, "wb+") as file_object:
                file_object.write(await attachment.read())

            attachment_info.append(
                {
                    "name": attachment.filename,
                    "path": str(file_location),
                    "type": attachment.content_type,
                }
            )

        return attachment_info

    @staticmethod
    async def create_event(
        event_data: EventCreateModel, attachments: List[UploadFile] = None
    ) -> GenericResponseModel:
        """
        Create a new event with attachments.

        Args:
            event_data (EventCreateModel): Data for the new event.
            attachments (List[UploadFile], optional): List of file attachments.

        Returns:
            GenericResponseModel: The created event wrapped in a response model.

        Raises:
            CustomBadRequestException: If the user is not authenticated.
            CustomInternalServerErrorException: If the event cannot be created.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        attachment_info = (
            await EventService.handle_attachments(attachments) if attachments else []
        )

        new_event = Event.create_new_event(event_data, attachment_info)
        if not new_event:
            logger.error("Failed to create new event")
            raise CustomInternalServerErrorException(ResponseMessages.ERR_CREATE_EVENT)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} created event: {new_event['id']}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_CREATE_EVENT,
            status_code=status.HTTP_201_CREATED,
            data=new_event,
        )

    @staticmethod
    async def update_event(
        event_id: int,
        event_data: EventUpdateModel,
        existing_attachment_ids: List[int],
        new_attachments: List[UploadFile] = None,
    ) -> GenericResponseModel:
        """
        Update an existing event with attachments.

        Args:
            event_id (int): ID of the event to update.
            event_data (EventUpdateModel): Updated event data.
            existing_attachment_ids (List[int]): List of IDs of attachments to keep.
            new_attachments (List[UploadFile], optional): List of new file attachments.

        Returns:
            GenericResponseModel: The updated event wrapped in a response model.

        Raises:
            CustomBadRequestException: If the user is not authenticated or the event does not exist.
            CustomInternalServerErrorException: If the event update fails.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        existing_event = Event.get_event_by_id(event_id)
        if not existing_event:
            logger.error(f"Event not found for update: {event_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

        # Handle new attachments
        new_attachment_info = []
        if new_attachments:
            new_attachment_info = await EventService.handle_attachments(new_attachments)

        updated_event = Event.update_event_by_id(
            event_id, event_data, existing_attachment_ids, new_attachment_info
        )
        if not updated_event:
            logger.error(f"Error updating event: {event_id}")
            raise CustomInternalServerErrorException(ResponseMessages.ERR_UPDATE_EVENT)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} updated event: {event_id}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_UPDATE_EVENT,
            status_code=status.HTTP_200_OK,
            data=updated_event,
        )

    @staticmethod
    def delete_event(event_id: int) -> GenericResponseModel:
        """
        Delete an existing event.

        Args:
            event_id (int): ID of the event to delete.

        Returns:
            GenericResponseModel: Confirmation of deletion wrapped in a response model.

        Raises:
            CustomBadRequestException: If the user is not authenticated or the event does not exist.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        success = Event.delete_event_by_id(event_id)
        if not success:
            logger.error(f"Event not found for deletion: {event_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} deleted event: {event_id}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_DELETE_EVENT,
            status_code=status.HTTP_200_OK,
            data={"event_id": event_id},
        )

    @staticmethod
    def get_event_by_id(event_id: int) -> GenericResponseModel:
        """
        Retrieve an event by ID.

        Args:
            event_id (int): ID of the event to retrieve.

        Returns:
            GenericResponseModel: The retrieved event wrapped in a response model.

        Raises:
            CustomBadRequestException: If the user is not authenticated or the event does not exist.
        """
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        event = Event.get_event_by_id(event_id)
        if not event:
            logger.error(f"Event not found: {event_id}")
            raise CustomBadRequestException(ResponseMessages.ERR_EVENT_NOT_FOUND)

        logger.info(
            f"User ID {context_actor_user_data.get().user_id} retrieved event: {event_id}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_EVENT,
            status_code=status.HTTP_200_OK,
            data=event,
        )

    @staticmethod
    def get_all_events(
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Retrieve all events with pagination, filtering, and sorting.
    
        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.
    
        Returns:
            GenericResponseModel: A GenericResponseModel with the list of events and pagination info.
        """
        events, total_count = Event.get_events(
            current_page,
            items_per_page,
            filter_params,
            sorting_params,
        )
    
        total_pages = math.ceil(total_count / items_per_page)
    
        logger.info(
            f"Events retrieved. Page: {current_page}, Items: {items_per_page}, Total: {total_count}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_ALL_EVENTS,
            status_code=status.HTTP_200_OK,
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_count,
                items=events,
            ),
        )
    
    @staticmethod
    def get_organizer_events(
        organizer_id: int,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Retrieve events for a specific organizer with pagination, filtering, and sorting.
    
        Args:
            organizer_id (int): The ID of the organizer.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Union[str, List[str]]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.
    
        Returns:
            GenericResponseModel: A GenericResponseModel with the list of events and pagination info.
        """
        events, total_count = Event.get_organizer_events(
            organizer_id,
            current_page,
            items_per_page,
            filter_params,
            sorting_params,
        )
    
        total_pages = math.ceil(total_count / items_per_page)
    
        logger.info(
            f"Organizer events retrieved. Organizer ID: {organizer_id}, Page: {current_page}, Items: {items_per_page}, Total: {total_count}"
        )
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_ORGANIZER_EVENTS,
            status_code=status.HTTP_200_OK,
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_count,
                items=events,
            ),
        )