import app.api.v1.endpoints
import app.logger
from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile
from app.service.event_service import EventService
from app.models.response import GenericResponseModel, build_api_response
from app.models.event import (
    EventCreateModel,
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

router = APIRouter()


@router.post(
    "/",
    status_code=201,
    response_model=GenericResponseModel,
    summary="Create new event.",
    description="Create a new event with the provided event data and attachments.",
    responses={
        201: {
            "model": GenericResponseModel,
            "description": "Successful creation of event",
        },
        400: {
            "model": GenericResponseModel,
            "description": "Invalid input data",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def create_event(
    title: str = Form("Debug Event"),
    date: datetime = Form(default_factory=lambda: datetime.now() + timedelta(days=7)),
    time: datetime = Form(
        default_factory=lambda: datetime.now().replace(
            hour=12, minute=0, second=0, microsecond=0
        )
    ),
    address: str = Form("Debug Address"),
    city: str = Form("Debug City"),
    latitude: float = Form(50.0755),
    longitude: float = Form(14.4378),
    capacity: int = Form(100),
    description: str = Form("This is a debug event description"),
    annotation: str = Form("Short debug annotation"),
    target_group: TargetGroup = Form(TargetGroup.ALL),
    event_type: EventType = Form(EventType.CONCERT),
    duration: float = Form(2.0),
    parent_info: str = Form("Debug Parent Info"),
    organizer_id: int = Form(1),
    attachments: List[UploadFile] = File(None),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Create a new event with attachments.
    """
    event_data = EventCreateModel(
        title=title,
        date=date,
        time=time,
        address=address,
        city=city,
        latitude=latitude,
        longitude=longitude,
        capacity=capacity,
        description=description,
        annotation=annotation,
        target_group=target_group,
        event_type=event_type,
        duration=duration,
        parent_info=parent_info,
        organizer_id=organizer_id,
    )

    response: GenericResponseModel = await EventService.create_event(
        event_data, attachments
    )
    return build_api_response(response)


@router.put(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Update existing event.",
    description="Update an existing event with the provided event data and attachments.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful update of event",
        },
        400: {
            "model": GenericResponseModel,
            "description": "Invalid input data or event not found",
        },
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def update_event(
    event_id: int,
    title: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    time: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    capacity: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    annotation: Optional[str] = Form(None),
    target_group: Optional[TargetGroup] = Form(None),
    event_type: Optional[EventType] = Form(None),
    duration: Optional[float] = Form(None),
    parent_info: Optional[str] = Form(None),
    new_attachments: List[UploadFile] = File(None),
    existing_attachment_ids: str = Form(None),
    organizer_id: Optional[int] = Form(None),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Update an existing event with attachments.
    """
    event_data = {
        k: v
        for k, v in locals().items()
        if v is not None
        and k
        not in ["event_id", "new_attachments", "existing_attachment_ids", "auth", "_"]
    }

    event_update_model = EventUpdateModel(**event_data)
    print("Route existing_attachment_ids: ", existing_attachment_ids)
    # Parse the existing attachment IDs
    try:
        existing_attachment_ids = (
            json.loads(existing_attachment_ids) if existing_attachment_ids else []
        )
    except json.JSONDecodeError:
        raise CustomBadRequestException(ResponseMessages.ERR_INVALID_DATA)

    response: GenericResponseModel = await EventService.update_event(
        event_id, event_update_model, existing_attachment_ids, new_attachments
    )
    return build_api_response(response)


@router.get(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get event by ID.",
    description="Retrieve an event by its ID.",
    responses={
        200: {
            "model": GenericResponseModel[EventModel],
            "description": "Successful retrieval of event",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Event not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_event(
    event_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve an event by ID.
    """
    response: GenericResponseModel = EventService.get_event_by_id(event_id)
    return build_api_response(response)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Delete event.",
    description="Delete an existing event by its ID.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful deletion of event",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Event not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def delete_event(
    event_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Delete an existing event.
    """
    response: GenericResponseModel = EventService.delete_event(event_id)
    return build_api_response(response)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get all events.",
    description="Retrieve all events with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of events",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_all_events(
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(
        None, alias="filter_params", description="JSON string of filter parameters"
    ),
    sorting_params: Optional[str] = Query(
        None, alias="sorting_params", description="JSON string of sorting parameters"
    ),
    date_from: Optional[datetime] = Query(
        None, description="Start date for filtering events"
    ),
    date_to: Optional[datetime] = Query(
        None, description="End date for filtering events"
    ),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all events with pagination, filtering, and sorting.

    This endpoint allows fetching events with various filtering options including date range.
    It also supports pagination and sorting of results.

    Args:
        current_page (int): The current page number for pagination.
        items_per_page (int): The number of items to display per page.
        filter_params (Optional[str]): JSON string containing filter parameters.
        sorting_params (Optional[str]): JSON string containing sorting parameters.
        date_from (Optional[datetime]): Start date for filtering events.
        date_to (Optional[datetime]): End date for filtering events.

    Returns:
        GenericResponseModel: A response model containing the list of events and pagination information.
    """
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    # Add date filtering to filter_params if provided
    if date_from or date_to:
        if not filters:
            filters = {}
        filters["event_dates"] = {}
        if date_from:
            filters["event_dates"]["date_from"] = date_from.isoformat()
        if date_to:
            filters["event_dates"]["date_to"] = date_to.isoformat()

    response = EventService.get_all_events(
        current_page,
        items_per_page,
        filters,
        sorting,
    )
    return build_api_response(response)

@router.get(
    "/organizer/{organizer_id}/events",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get organizer's events.",
    description="Retrieve events for the specified organizer with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of organizer's events",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_organizer_events(
    organizer_id: int,
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(
        None, alias="filter_params", description="JSON string of filter parameters"
    ),
    sorting_params: Optional[str] = Query(
        None, alias="sorting_params", description="JSON string of sorting parameters"
    ),
    date_from: Optional[datetime] = Query(
        None, description="Start date for filtering events"
    ),
    date_to: Optional[datetime] = Query(
        None, description="End date for filtering events"
    ),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve events for the specified organizer with pagination, filtering, and sorting.

    Args:
        organizer_id (int): The ID of the organizer.
        current_page (int): The current page number for pagination.
        items_per_page (int): The number of items to display per page.
        filter_params (Optional[str]): JSON string containing filter parameters.
        sorting_params (Optional[str]): JSON string containing sorting parameters.
        date_from (Optional[datetime]): Start date for filtering events.
        date_to (Optional[datetime]): End date for filtering events.

    Returns:
        GenericResponseModel: A response model containing the list of events and pagination information.
    """
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    # Add date filtering to filter_params if provided
    if date_from or date_to:
        if not filters:
            filters = {}
        filters["event_dates"] = {}
        if date_from:
            filters["event_dates"]["date_from"] = date_from.isoformat()
        if date_to:
            filters["event_dates"]["date_to"] = date_to.isoformat()

    response = EventService.get_organizer_events(
        organizer_id,
        current_page,
        items_per_page,
        filters,
        sorting,
    )
    return build_api_response(response)