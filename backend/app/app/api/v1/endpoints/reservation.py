from typing import Optional
from app.models.get_params import parse_json_params
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.service.reservation_service import ReservationService
from app.models.response import GenericResponseModel
from app.models.reservation import ReservationCreateModel, ReservationModel
from app.dependencies import get_db, authenticate_user_token
from app.context_manager import build_request_context
from app.models.response import build_api_response

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel,
    summary="Create new reservation.",
    description="Create a new reservation with the provided reservation data.",
    responses={
        201: {
            "model": GenericResponseModel[ReservationModel],
            "description": "Successful creation of reservation",
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
async def create_reservation(
    reservation_data: ReservationCreateModel,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Create a new reservation.

    Args:
        reservation_data (ReservationCreateModel): Data for the new reservation.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing the created reservation.
    """
    response = ReservationService.create_reservation(db, reservation_data)
    return build_api_response(response)


@router.get(
    "/{reservation_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get reservation by ID.",
    description="Retrieve a reservation by its ID.",
    responses={
        200: {
            "model": GenericResponseModel[ReservationModel],
            "description": "Successful retrieval of reservation",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Reservation not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve a reservation by ID.

    Args:
        reservation_id (int): ID of the reservation to retrieve.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing the reservation.
    """
    response = ReservationService.get_reservation_by_id(db, reservation_id)
    return build_api_response(response)


@router.delete(
    "/{reservation_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Delete reservation.",
    description="Delete an existing reservation by its ID.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful deletion of reservation",
        },
        404: {
            "model": GenericResponseModel,
            "description": "Reservation not found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def delete_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Delete a reservation by ID.

    Args:
        reservation_id (int): ID of the reservation to delete.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response confirming deletion.
    """
    response = ReservationService.delete_reservation(db, reservation_id)
    return build_api_response(response)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get all reservations.",
    description="Retrieve all reservations with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of reservations",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_all_reservations(
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(None, alias="filter_params"),
    sorting_params: Optional[str] = Query(None, alias="sorting_params"),
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all reservations with pagination, filtering, and sorting.

    Args:
        current_page (int): The page number of the results.
        items_per_page (int): The number of results per page.
        filter_params (Optional[str]): The filter parameters for the query.
        sorting_params (Optional[str]): The sorting parameters for the query.
        db (Session): The database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing all reservations.
    """
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    response = ReservationService.get_all_reservations(
        db, current_page, items_per_page, filters, sorting
    )
    return build_api_response(response)


@router.get(
    "/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get all reservations for a specific event.",
    description="Retrieve all reservations for a specific event with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of reservations for the event",
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
async def get_reservations_by_event_id(
    event_id: int,
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(None, alias="filter_params"),
    sorting_params: Optional[str] = Query(None, alias="sorting_params"),
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all reservations for a specific event with pagination, filtering, and sorting.

    Args:
        event_id (int): The ID of the event to get reservations for.
        current_page (int): The page number of the results.
        items_per_page (int): The number of results per page.
        filter_params (Optional[str]): The filter parameters for the query.
        sorting_params (Optional[str]): The sorting parameters for the query.
        db (Session): The database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing all reservations for the specified event.
    """
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    response = ReservationService.get_reservations_by_event_id(
        db, event_id, current_page, items_per_page, filters, sorting
    )
    return build_api_response(response)
