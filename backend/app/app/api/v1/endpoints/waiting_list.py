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
    "/",
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
    "/{event_date_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get waiting list for event date",
    description="Retrieve the waiting list for a specific event date with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
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
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(
        None, alias="filter_params", description="JSON string of filter parameters"
    ),
    sorting_params: Optional[str] = Query(
        None, alias="sorting_params", description="JSON string of sorting parameters"
    ),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve the waiting list for a specific event date with pagination, filtering, and sorting.

    This endpoint allows authenticated users to view the waiting list for a given event date.
    It supports pagination, filtering, and sorting of the results.

    Args:
        event_date_id (int): The ID of the event date to retrieve the waiting list for.
        current_page (int): The current page number for pagination.
        items_per_page (int): The number of items to display per page.
        filter_params (Optional[str]): JSON string containing filter parameters.
        sorting_params (Optional[str]): JSON string containing sorting parameters.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the paginated list of waiting list entries.

    Raises:
        HTTPException:
            - 404: If the event date is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes a paginated list of waiting list entries for the specified event date.
    """
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    response: GenericResponseModel = WaitingListService.get_waiting_list(
        event_date_id, current_page, items_per_page, filters, sorting
    )
    return build_api_response(response)

@router.put(
    "/{waiting_list_id}",
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
    "/{event_date_id}/process",
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


@router.get(
    "/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get user's waiting list entries",
    description="Retrieve all waiting list entries for a specific user.",
    responses={
        200: {
            "model": GenericResponseModel[List[WaitingListModel]],
            "description": "Successfully retrieved user's waiting list entries",
        },
        404: {
            "model": GenericResponseModel,
            "description": "User not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_user_waiting_list_entries(
    user_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all waiting list entries for a specific user.

    This endpoint allows authenticated users to view all their waiting list entries across different events.

    Args:
        user_id (int): The ID of the user to retrieve waiting list entries for.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the list of waiting list entries for the user.

    Raises:
        HTTPException: 
            - 404: If the user is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes a list of all waiting list entries for the specified user.
    """
    response: GenericResponseModel = WaitingListService.get_user_waiting_list_entries(user_id)
    return build_api_response(response)



@router.delete(
    "/{waiting_list_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Delete waiting list entry",
    description="Delete a specific waiting list entry.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successfully deleted waiting list entry",
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
async def delete_waiting_list_entry(
    waiting_list_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Delete a specific waiting list entry.

    This endpoint allows authenticated users to delete their waiting list entry.

    Args:
        waiting_list_id (int): The ID of the waiting list entry to delete.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model confirming the deletion.

    Raises:
        HTTPException: 
            - 404: If the waiting list entry is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response confirms the successful deletion of the waiting list entry.
    """
    response: GenericResponseModel = WaitingListService.delete_waiting_list_entry(waiting_list_id)
    return build_api_response(response)


@router.get(
    "/by-event-date/{event_date_id}/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=WaitingListModel,
    summary="Get waiting list entry by event date and user",
    description="Retrieve a waiting list entry for a specific event date and user.",
    responses={
        200: {
            "model": WaitingListModel,
            "description": "Successfully retrieved waiting list entry",
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
async def get_waiting_list_entry_by_event_date_and_user(
    event_date_id: int,
    user_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> WaitingListModel:
    """
    Retrieve a waiting list entry for a specific event date and user.

    This endpoint allows authenticated users to retrieve a waiting list entry
    for a given event date and user.

    Args:
        event_date_id (int): The ID of the event date.
        user_id (int): The ID of the user.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        WaitingListResponseModel: A response model containing the waiting list entry details.

    Raises:
        HTTPException: 
            - 404: If the waiting list entry is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
    """
    response: WaitingListModel = WaitingListService.get_waiting_list_entry_by_event_date_and_user(event_date_id, user_id)
    return build_api_response(response)

@router.get(
    "/entry/{waiting_list_id}",
    status_code=status.HTTP_200_OK,
    response_model=WaitingListModel,
    summary="Get waiting list entry by ID",
    description="Retrieve a waiting list entry by its ID.",
    responses={
        200: {
            "model": WaitingListModel,
            "description": "Successfully retrieved waiting list entry",
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
async def get_waiting_list_entry_by_id(
    waiting_list_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> WaitingListModel:
    """
    Retrieve a waiting list entry by its ID.

    This endpoint allows authenticated users to retrieve a waiting list entry
    by its unique identifier.

    Args:
        waiting_list_id (int): The ID of the waiting list entry.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        WaitingListResponseModel: A response model containing the waiting list entry details.

    Raises:
        HTTPException: 
            - 404: If the waiting list entry is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
    """
    response: WaitingListModel = WaitingListService.get_waiting_list_entry_by_id(waiting_list_id)
    return build_api_response(response)