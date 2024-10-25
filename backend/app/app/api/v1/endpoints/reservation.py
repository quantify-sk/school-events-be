from http.client import HTTPException
from typing import Dict, List, Optional, Union
from app.models.get_params import parse_json_params
from app.utils.exceptions import CustomBadRequestException
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.service.reservation_service import ReservationService
from app.models.response import GenericResponseModel
from app.models.reservation import (
    ReservationCreateModel,
    ReservationModel,
    ReservationUpdateModel,
)
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


@router.get(
    "/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get user reservations.",
    description="Retrieve all reservations for a specific user.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of user reservations",
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
async def get_user_reservations(
    user_id: int,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve all reservations for a specific user.

    Args:
        user_id (int): ID of the user to retrieve reservations for.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing the user's reservations.
    """
    response = ReservationService.get_user_reservations(db, user_id)
    return response


@router.get(
    "/user/{user_id}/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get reservation for user and event.",
    description="Retrieve a reservation for a specific user and event.",
    responses={
        200: {
            "model": GenericResponseModel,
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
async def get_reservation_for_user_and_event(
    user_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Retrieve a reservation for a specific user and event.

    Args:
        user_id (int): ID of the user.
        event_id (int): ID of the event.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing the reservation.
    """
    response = ReservationService.get_reservation_for_user_and_event(
        db, user_id, event_id
    )
    return response


@router.put(
    "/{reservation_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Update reservation by ID.",
    description="Update a reservation by its ID.",
    responses={
        200: {
            "model": GenericResponseModel[ReservationModel],
            "description": "Successful update of reservation",
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
async def update_reservation(
    reservation_id: int,
    reservation_data: ReservationUpdateModel,
    db: Session = Depends(get_db),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Update a reservation by ID.

    Args:
        reservation_id (int): ID of the reservation to update.
        reservation_data (ReservationUpdateModel): Updated reservation data.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response containing the updated reservation.
    """
    response = ReservationService.update_reservation(
        db, reservation_id, reservation_data
    )
    return build_api_response(response)


@router.get(
    "/user/{user_id}/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get paginated reservations for user and event.",
    description="Retrieve paginated reservations for a specific user and event.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successful retrieval of paginated reservations",
        },
        404: {
            "model": GenericResponseModel,
            "description": "No reservations found",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_reservations_for_user_and_event(
    user_id: int,
    event_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    filter_params: Optional[Dict[str, Union[str, List[str]]]] = None,
    sorting_params: Optional[List[Dict[str, str]]] = None,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    try:
        response = ReservationService.get_reservations_for_user_and_event(
            user_id, event_id, page, items_per_page, filter_params, sorting_params
        )
        print(response)
        if response.data.total_items == 0:
            response.message = "No reservations found"
            response.status_code = status.HTTP_404_NOT_FOUND
        return build_api_response(response)
    except CustomBadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/code/{reservation_code}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Find Reservation by Code",
    description="Find a reservation by its local reservation code.",
)
async def find_reservation_by_code(
    reservation_code: str,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Find a reservation by its local reservation code.

    This endpoint requires authentication and returns the reservation details.

    Args:
        reservation_code (str): The local reservation code to search for.

    Returns:
        GenericResponseModel: A response model containing the reservation details.
    """
    response = ReservationService.find_reservation_by_code(reservation_code)
    return response


@router.put(
    "/{reservation_id}/confirm/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Confirm Reservation",
    description="Confirm a reservation by its ID.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Reservation confirmed",
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
async def confirm_reservation(
    reservation_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Confirm a reservation by its ID.

    Args:
        reservation_id (int): ID of the reservation to confirm.
        db (Session): Database session.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response confirming the reservation.
    """
    response = ReservationService.confirm_reservation(reservation_id)
    return build_api_response(response)


@router.put(
    "/{reservation_id}/reject/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Reject Reservation",
    description="Reject a reservation by its ID.",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Reservation rejected",
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
async def reject_reservation(
    reservation_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Reject a reservation by its ID.

    Args:
        reservation_id (int): ID of the reservation to reject.
        auth (Depends): The authentication token.
        _ (Depends): The request context.

    Returns:
        GenericResponseModel: The response confirming the rejection.
    """
    response = ReservationService.reject_reservation(reservation_id)
    return build_api_response(response)