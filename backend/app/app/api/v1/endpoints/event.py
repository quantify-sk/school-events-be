import app.api.v1.endpoints
import app.logger
from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile
from app.service.event_service import EventService
from app.models.response import GenericResponseModel, build_api_response
from app.models.event import (
    ClaimStatus,
    EventClaimCreateModel,
    EventClaimModel,
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
from fastapi import Body

import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse

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
    title: str = Form(...),
    address: str = Form(...),
    city: str = Form(...),
    capacity: int = Form(...),
    description: str = Form(...),
    annotation: str = Form(...),
    parent_info: str = Form(None),
    target_group: TargetGroup = Form(...),
    age_from: int = Form(...),
    age_to: Optional[int] = Form(None),
    event_type: EventType = Form(...),
    duration: int = Form(...),  # Duration in minutes
    more_info_url: Optional[str] = Form(None),
    organizer_id: int = Form(...),
    ztp_access: bool = Form(None),
    parking_spaces: int = Form(None),
    event_dates: str = Form(...),
    attachments: List[UploadFile] = File(None),
    region: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Create a new event with attachments.
    """
    try:
        parsed_event_dates = json.loads(event_dates)
        event_date_models = [
            EventDateModel(
                id=0,  # Temporary ID, will be replaced by the database
                event_id=0,  # Temporary event_id, will be replaced by the database
                date=datetime.strptime(date["date"], "%Y-%m-%d").date(),
                time=datetime.strptime(date["time"], "%H:%M").time(),
                capacity=capacity,
                available_spots=capacity,
            )
            for date in parsed_event_dates
        ]
    except (json.JSONDecodeError, ValueError) as e:
        raise CustomBadRequestException(f"Invalid event dates: {str(e)}")

    try:
        print(parking_spaces, ztp_access)
        event_data = EventCreateModel(
            title=title,
            institution_name="Default Institution",  # You can replace this with a default value or get it from somewhere else
            address=address,
            city=city,
            capacity=capacity,
            description=description,
            annotation=annotation,
            parent_info=parent_info,
            target_group=target_group,
            age_from=age_from,
            age_to=age_to,
            event_type=event_type,
            duration=duration,
            more_info_url=more_info_url,
            organizer_id=organizer_id,
            event_dates=event_date_models,
            parking_spaces=parking_spaces,
            ztp_access=ztp_access,
            region=region,
            district=district,
        )
    except ValidationError as e:
        raise CustomBadRequestException(f"Invalid event data: {str(e)}")

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
    institution_name: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    capacity: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    annotation: Optional[str] = Form(None),
    parent_info: Optional[str] = Form(None),
    target_group: Optional[TargetGroup] = Form(None),
    age_from: Optional[int] = Form(None),
    age_to: Optional[int] = Form(None),
    status: Optional[EventStatus] = Form(None),
    event_type: Optional[EventType] = Form(None),
    duration: Optional[int] = Form(None),
    more_info_url: Optional[str] = Form(None),
    organizer_id: Optional[int] = Form(None),
    ztp_access: Optional[bool] = Form(None),
    parking_spaces: Optional[int] = Form(None),
    new_attachments: List[UploadFile] = File(None),
    existing_attachment_ids: str = Form(None),
    event_dates: str = Form(None),
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
        not in [
            "event_id",
            "new_attachments",
            "existing_attachment_ids",
            "event_dates",
            "auth",
            "_",
        ]
    }
    print("Event data:", event_data)

    # Parse the existing attachment IDs
    try:
        existing_attachment_ids = (
            json.loads(existing_attachment_ids) if existing_attachment_ids else []
        )
    except json.JSONDecodeError:
        raise CustomBadRequestException(ResponseMessages.ERR_INVALID_DATA)

    print("Existing attachments:", existing_attachment_ids)

    print("Event dates:", event_dates)
    # Parse the event dates
    if event_dates:
        try:
            parsed_event_dates = json.loads(event_dates)
            event_date_models = []
            for date_item in parsed_event_dates:
                # Parse date
                date_obj = datetime.strptime(date_item["date"], "%Y-%m-%d").date()

                # Parse time
                time_obj = datetime.strptime(date_item["time"], "%H:%M").time()

                event_date_models.append(
                    EventDateModel(
                        id=date_item.get("id"),
                        event_id=event_id,
                        date=date_obj,
                        time=time_obj,
                        capacity=date_item.get("capacity"),
                        available_spots=date_item.get("available_spots"),
                        lock_time=date_item.get("lock_time"),
                    )
                )
            event_data["event_dates"] = event_date_models
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error parsing event dates: {str(e)}")
            print(f"Problematic date item: {date_item}")
            raise CustomBadRequestException(f"Invalid event date format: {str(e)}")

        print("Event dates parsing:", event_date_models)

    try:
        event_update_model = EventUpdateModel(**event_data)
        print("ENDPOINT EVENT UPDATE MODEL", event_update_model)
    except ValidationError as e:
        print(f"Validation error: {str(e)}")
        raise CustomBadRequestException(f"Invalid event data: {str(e)}")

    print("Event update model:", event_update_model)

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
    admin: bool = Query(False, description="Flag to indicate if the user is an admin"),
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
        current_page, items_per_page, filters, sorting, admin
    )
    return build_api_response(response)


@router.get(
    "/with-dates/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get all events with dates.",
    description="Retrieve all events along with their dates with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of events with dates",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_all_events_with_dates(
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
    admin: bool = Query(False, description="Flag to indicate if the user is an admin"),
    _=Depends(build_request_context),
    auth=Depends(authenticate_user_token),
) -> GenericResponseModel:
    """
    Retrieve all events along with their dates with pagination, filtering, and sorting.

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

    # Call the service function to get events with their dates
    response = EventService.get_all_events_with_dates(
        current_page, items_per_page, filters, sorting, admin
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


@router.get(
    "/{event_date_id}/event-date/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get event date by ID.",
    description="Retrieve an event date by its ID.",
    responses={
        200: {
            "model": GenericResponseModel[EventDateModel],
            "description": "Successful retrieval of event date",
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
async def get_event_date(
    event_date_id: int,
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve an event date by ID.

    This endpoint allows authenticated users to retrieve details of a specific event date.

    Args:
        event_date_id (int): The unique identifier of the event date to retrieve.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A generic response model containing the event date details.

    Raises:
        HTTPException:
            - 404: If the event date with the given ID is not found.
            - 500: If there's an internal server error during the process.

    Note:
        - This endpoint requires user authentication.
        - The response includes detailed information about the event date, such as the associated event,
          date, time, capacity, and available spots.
    """
    response: GenericResponseModel = EventService.get_event_date_by_id(event_date_id)
    return build_api_response(response)


@router.post(
    "/claims",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel,
    summary="Create a new claim",
    description="Create a new claim for creating, updating, or cancelling an event.",
    responses={
        201: {
            "model": GenericResponseModel[EventClaimModel],
            "description": "Successful creation of claim",
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
async def create_claim(
    claim_data: EventClaimCreateModel,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Create a new claim for an event.

    Args:
        claim_data (EventClaimCreateModel): Data for creating the claim.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A response containing the created claim data.
    """
    response: GenericResponseModel = await EventService.create_claim(claim_data)
    return build_api_response(response)


@router.get(
    "/claims/pending",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get pending claims",
    description="Retrieve all pending claims for events.",
    responses={
        200: {
            "model": GenericResponseModel[List[EventClaimModel]],
            "description": "Successful retrieval of pending claims",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_pending_claims(
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all pending claims.

    Args:
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A response containing a list of pending claims.
    """
    response: GenericResponseModel = await EventService.get_pending_claims()
    return build_api_response(response)


@router.put(
    "/claims/{claim_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Update claim status",
    description="Update the status of a claim.",
    responses={
        200: {
            "model": GenericResponseModel[EventClaimModel],
            "description": "Successful update of claim status",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Claim not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def update_claim_status(
    claim_id: int,
    new_status: ClaimStatus = Body(..., embed=True),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Update the status of a claim.

    Args:
        claim_id (int): The ID of the claim to update.
        new_status (ClaimStatus): The new status to set for the claim.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A response containing the updated claim data.
    """
    response: GenericResponseModel = await EventService.update_claim_status(
        claim_id, new_status
    )
    return build_api_response(response)


@router.post(
    "/{event_date_id}/mark-as-paid",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Mark event as paid.",
    description="Mark a COMPLETED_UNPAID event as COMPLETED_PAYMENT_SENT by an admin.",
    responses={
        200: {
            "model": GenericResponseModel[EventModel],
            "description": "Successfully marked event as paid",
        },
        400: {
            "model": GenericResponseModel,
            "description": "Event not found or invalid status",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def mark_event_as_paid(
    event_date_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Mark an event as paid by an admin.
    """
    print("EVENT DATE ID", event_date_id)
    response: GenericResponseModel = await EventService.mark_as_paid(event_date_id)
    return build_api_response(response)


@router.post(
    "/{event_date_id}/mark-as-completed",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Mark event as completed.",
    description="Mark a COMPLETED_PAYMENT_SENT event as COMPLETED by an admin.",
    responses={
        200: {
            "model": GenericResponseModel[EventModel],
            "description": "Successfully marked event as completed",
        },
        400: {
            "model": GenericResponseModel,
            "description": "Event not found or invalid status",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def mark_event_as_completed(
    event_date_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Mark an event as completed by an admin.
    """
    response: GenericResponseModel = await EventService.mark_as_completed(event_date_id)
    return build_api_response(response)



@router.post("/export")
async def export_events_to_excel(data: List[dict]):
    # Create DataFrame from the data
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Podujatia', index=False)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Podujatia']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        # Format the header row
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, len(value) + 5)  # Adjust column width
    
    # Prepare the response
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename=events_export.xlsx'
    }
    
    return StreamingResponse(
        output, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )