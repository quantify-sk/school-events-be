import app.api.v1.endpoints
import app.logger
from datetime import datetime, timedelta
import json
from app.models.waiting_list import WaitingListModel, WaitingListCreateModel, WaitingListUpdateModel
from app.service.waiting_list_service import WaitingListService
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile
from app.service.event_service import EventService
from app.models.response import GenericResponseModel, build_api_response
from app.models.event import (
    EventCreateModel,
    EventDateModel,
    EventStatus,
    EventUpdateModel,
    EventModel,
    EventType,
    TargetGroup,
)
from app.utils.response_messages import ResponseMessages
from app.models.get_params import parse_json_params
from app.dependencies import authenticate_user_token
from app.context_manager import build_request_context
from typing import Optional, List, Dict, Union
from pydantic import Json
from app.utils.exceptions import CustomBadRequestException
from app.logger import logger
from pydantic import ValidationError

router = APIRouter()

@router.post(
    "/waiting-list",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel,
    summary="Add to waiting list",
    description="Add a user to the waiting list for an event date.",
    responses={
        201: {
            "model": GenericResponseModel[WaitingListModel],
            "description": "Successfully added to waiting list",
        },
        400: {
            "model": GenericResponseModel,
            "description": "Bad request",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def add_to_waiting_list(
    waiting_list_entry: WaitingListCreateModel,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Add a user to the waiting list for an event date.

    This endpoint allows authenticated users to join the waiting list for a specific event date.

    Args:
        waiting_list_entry (WaitingListCreateModel): The details of the waiting list entry to create.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the created waiting list entry details.

    Raises:
        HTTPException: 
            - 400: If there's an error in the provided data.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes detailed information about the created waiting list entry.
    """
    response: GenericResponseModel = WaitingListService.add_to_waiting_list(waiting_list_entry)
    return build_api_response(response)

@router.get(
    "/waiting-list/{event_date_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get waiting list for event date",
    description="Retrieve the waiting list for a specific event date.",
    responses={
        200: {
            "model": GenericResponseModel[List[WaitingListModel]],
            "description": "Successfully retrieved waiting list",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Event date not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_waiting_list(
    event_date_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve the waiting list for a specific event date.

    This endpoint allows authenticated users to view the waiting list for a given event date.

    Args:
        event_date_id (int): The ID of the event date to retrieve the waiting list for.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the list of waiting list entries.

    Raises:
        HTTPException: 
            - 404: If the event date is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes a list of waiting list entries for the specified event date.
    """
    response: GenericResponseModel = WaitingListService.get_waiting_list(event_date_id)
    return build_api_response(response)

@router.put(
    "/waiting-list/{waiting_list_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Update waiting list entry",
    description="Update an existing waiting list entry.",
    responses={
        200: {
            "model": GenericResponseModel[WaitingListModel],
            "description": "Successfully updated waiting list entry",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Waiting list entry not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def update_waiting_list_entry(
    waiting_list_id: int,
    waiting_list_update: WaitingListUpdateModel,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Update an existing waiting list entry.

    This endpoint allows authenticated users to update their waiting list entry.

    Args:
        waiting_list_id (int): The ID of the waiting list entry to update.
        waiting_list_update (WaitingListUpdateModel): The updated details for the waiting list entry.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the updated waiting list entry details.

    Raises:
        HTTPException: 
            - 404: If the waiting list entry is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes the updated waiting list entry details.
    """
    response: GenericResponseModel = WaitingListService.update_waiting_list_entry(waiting_list_id, waiting_list_update)
    return build_api_response(response)

@router.post(
    "/waiting-list/{event_date_id}/process",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Process waiting list",
    description="Process the waiting list for a specific event date.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successfully processed waiting list",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Event date not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def process_waiting_list(
    event_date_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Process the waiting list for a specific event date.

    This endpoint allows authenticated users to trigger the processing of the waiting list
    for a given event date. It will attempt to create reservations for waiting list entries
    if spots have become available.

    Args:
        event_date_id (int): The ID of the event date to process the waiting list for.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the number of processed entries.

    Raises:
        HTTPException: 
            - 404: If the event date is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes the number of waiting list entries that were processed.
    """
    response: GenericResponseModel = WaitingListService.process_waiting_list(event_date_id)
    return build_api_response(response)