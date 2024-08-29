import json
from typing import Optional, List

from app.context_manager import build_request_context
from app.dependencies import authenticate_user_token
from app.models.get_params import parse_json_params
from app.models.response import (
    GenericResponseModel,
    PaginationResponseDataModel,
    build_api_response,
)
from app.models.user import (
    UserCreateModel,
    UserModel,
    UserUpdateModel,
)
from app.service.user_service import UserService
from app.utils.response_messages import ResponseMessages
from fastapi import APIRouter, Depends, Query, status

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Create new user.",
    description="Create a new user with the provided user_id and user_data.",
    responses={
        200: {
            "model": GenericResponseModel[UserModel],
            "description": "Successful creation of user",
        },
        400: {
            "model": GenericResponseModel,
            "description": ResponseMessages.ERR_EMAIL_ALREADY_TAKEN,
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
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
async def create_user(
    user_data: UserCreateModel,  # The data for creating the user.
    _=Depends(build_request_context),  # Build the request context.
) -> GenericResponseModel:  # The response containing the result of the operation.
    """Create a new user for a user.

    Args:
        user_data (UserCreateModel): The data for creating the user.
        auth (Depends): The authentication token.
        _ (Depends): Build the request context.

    Returns:
        GenericResponseModel: The response containing the result of the operation.
    """
    # Call the create_user method of the UserService class to create the user
    # The UserService.create_user method takes in the user_data and returns a GenericResponseModel
    response: GenericResponseModel = UserService.create_user(
        user_data,  # The data for creating the user.
    )

    # Build the response with the request context
    # The build_api_response function takes in the response and adds the request context to it
    return build_api_response(response)


@router.get(
    "/{user_id}/parent-organizer",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get Parent Organizer",
    description="Retrieve the parent organizer of a user by their ID.",
)
async def get_parent_organizer(
    user_id: int,
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),  # Build the request context.
):
    """
    Get the parent organizer of a user by their ID.

    This endpoint requires authentication and returns the parent organizer of the specified user.

    Args:
        user_id (int): The ID of the user whose parent organizer we want to retrieve.
        current_user (UserModel): The currently authenticated user (injected by dependency).

    Returns:
        GenericResponseModel: A response model containing the parent organizer.
    """
    response = UserService.get_parent_organizer(user_id)
    return response


@router.get(
    "/{user_id}/role",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get User Role",
    description="Retrieve the role of a user by their ID.",
)
async def get_user_role(
    user_id: int,
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),  # Build the request context.
):
    """
    Get the role of a user by their ID.

    This endpoint requires authentication and returns the role of the specified user.

    Args:
        user_id (int): The ID of the user whose role we want to retrieve.
        current_user (UserModel): The currently authenticated user (injected by dependency).

    Returns:
        GenericResponseModel: A response model containing the user's role.
    """
    response = UserService.get_user_role(user_id)
    return response


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get user by ID.",
    description="Get a user by ID.",
    responses={
        200: {
            "model": GenericResponseModel[UserModel],
            "description": "Successful retrieval of user",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
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
async def get_user_by_id(
    user_id: int,  # The ID of the user.
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),  # Build the request context.
) -> GenericResponseModel[UserModel]:
    """
    Get a user by ID.

    Args:
        user_id (int): The ID of the user.

    Returns:
        GenericResponseModel: A GenericResponseModel with the user or an error.

    Raises:
        CustomInternalServerErrorException: If an error occur while getting the user.
    """
    # Call the get_user_by_id method of the UserService class to get the user
    response: GenericResponseModel = UserService.get_user_by_id(
        user_id,
    )

    # Return the response after adding the request context
    return build_api_response(response)


@router.delete(
    "/{user_id}",  # The user ID to be deleted.
    status_code=status.HTTP_200_OK,  # The HTTP status code for a successful operation.
    response_model=GenericResponseModel,  # The response model for the endpoint.
    summary="Delete user.",  # The summary or brief description of the endpoint.
    description="Delete user.",  # The detailed description of the endpoint.
    responses={  # The possible responses along with their status codes and models.
        200: {
            "model": GenericResponseModel[
                UserModel
            ],  # The model for the successful response.
            "description": "Successful delete user",  # The description for the successful response.
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
        },
        404: {
            "model": GenericResponseModel,  # The model for the not found response.
            "description": "User not found",  # The description for the not found response.
        },
        500: {
            "model": GenericResponseModel,  # The model for the internal server error response.
            "description": "Internal Server Error",  # The description for the internal server error response.
        },
    },
)
async def delete_user(
    user_id: int,  # The ID of the user to be deleted.
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),  # Build the request context.
) -> GenericResponseModel:  # The response containing the result of the operation.
    """
    Delete user.

    Deletes a user from the database.

    Args:
        user_id (int): The ID of the user to be deleted.
        auth (Depends): The authentication token.
        _ (Depends): Build the request context.

    Returns:
        GenericResponseModel: The response containing the result of the operation.
    """

    # Call the delete_user method of the UserService class to delete the user
    response: GenericResponseModel = UserService.delete_user(
        user_id,
    )

    # Return the response after adding the request context
    return build_api_response(response)


@router.put(
    "/{user_id}",
    status_code=status.HTTP_200_OK,  # The HTTP status code for a successful operation.
    response_model=GenericResponseModel,  # The response model for the endpoint.
    summary="Update user.",  # The summary or brief description of the endpoint.
    description="Update user.",  # The detailed description of the endpoint.
    responses={  # The possible responses along with their status codes and models.
        200: {
            "model": GenericResponseModel[
                UserModel
            ],  # The model for the successful response.
            "description": "Successful update user",  # The description for the successful response.
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
        },
        500: {
            "model": GenericResponseModel,  # The model for the internal server error response.
            "description": "Internal Server Error",  # The description for the internal server error response.
        },
    },
)
async def update_user(
    user_id: int,  # The ID of the user to be updated.
    user_data: UserUpdateModel,  # The data of the user to be updated.
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),  # Build the request context.
) -> GenericResponseModel:  # The response containing the result of the operation.
    """
    Update user.

    Updates a user in the database.

    Args:
        user_id (int): The ID of the user to be updated.
        user_data (UserUpdateModel): The data of the user to be updated.
        auth (Depends): The authentication token.
        _ (Depends): Build the request context.

    Returns:
        GenericResponseModel: The response containing the result of the operation.
    """

    # Call the update_user method of the UserService class to update the user
    print(user_data)
    response: GenericResponseModel = UserService.update_user(user_id, user_data)

    # Return the response after adding the request context
    return build_api_response(response)


@router.get(
    "s/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get all users.",
    description="Get all users.",
    responses={
        200: {
            "model": GenericResponseModel[PaginationResponseDataModel[list[UserModel]]],
            "description": "Successful get all users",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
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
async def get_all_users(
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(None, alias="filter_params"),
    sorting_params: Optional[str] = Query(None, alias="sorting_params"),
    auth=Depends(authenticate_user_token),  # The authentication token.
    _=Depends(build_request_context),
):
    """
    Get all users.

    This endpoint retrieves all users from the database. It supports pagination, filtering, and sorting.

    Parameters:
        - current_page (int): The page number of the results. Default is 1.
        - items_per_page (int): The number of results per page. Default is 10.
        - filter_params (Optional[str]): The filter parameters for the query.
        - sorting_params (Optional[str]): The sorting parameters for the query.
        - auth (Depends): The authentication token.
        - _ (Depends): The request context.

    Returns:
        GenericResponseModel: A GenericResponseModel containing the result of the operation.
            The response model is PaginationResponseDataModel[list[UserModel]].

    Responses:
        - 200: Successful get all users. The model is GenericResponseModel.
        - 401: Invalid authentication token. The model is GenericResponseModel.
        - 404: User not found. The model is GenericResponseModel.
        - 500: Internal Server Error. The model is GenericResponseModel.
    """
    # Parse filter_params and sorting_params
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    # Call the get_all_users method of the UserService class to get all users
    response: GenericResponseModel = UserService.get_all_users(
        current_page, items_per_page, filters, sorting
    )

    # Return the response after adding the request context
    return build_api_response(response)


@router.get(
    "/pending-approval/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Get pending approval requests",
    description="Get all user accounts pending approval with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel[PaginationResponseDataModel[List[UserModel]]],
            "description": "Successfully retrieved pending approval requests",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def get_pending_approval_requests(
    current_page: int = Query(1, ge=1, description="The page number to fetch"),
    items_per_page: int = Query(
        10, ge=1, le=100, description="The number of items per page"
    ),
    filter_params: Optional[str] = Query(
        None, description="JSON string of filter parameters"
    ),
    sorting_params: Optional[str] = Query(
        None, description="JSON string of sorting parameters"
    ),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Get pending approval requests.

    This endpoint retrieves all user accounts with pending approval status, with pagination, filtering, and sorting.

    Parameters:
        - current_page (int): The page number to fetch. Default is 1.
        - items_per_page (int): The number of items per page. Default is 10, maximum is 100.
        - filter_params (Optional[str]): JSON string of filter parameters.
        - sorting_params (Optional[str]): JSON string of sorting parameters.
        - auth (Depends): The authentication token.
        - _ (Depends): The request context.

    Returns:
        GenericResponseModel: A GenericResponseModel containing the result of the operation.
            The response model is a PaginationResponseDataModel containing a list of UserModel.

    Responses:
        - 200: Successfully retrieved pending approval requests. The model is GenericResponseModel.
        - 401: Invalid authentication token. The model is GenericResponseModel.
        - 500: Internal Server Error. The model is GenericResponseModel.
    """
    response: GenericResponseModel = UserService.get_pending_approval_requests(
        current_page,
        items_per_page,
        json.loads(filter_params) if filter_params else None,
        json.loads(sorting_params) if sorting_params else None,
    )
    return build_api_response(response)


@router.put(
    "/approve/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Approve a school representative account or organizer account",
    description="Approve a school representative account by changing its status to active.",
    responses={
        200: {
            "model": GenericResponseModel[UserModel],
            "description": "Successfully approved school representative account",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
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
async def approve_user(
    user_id: int,
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Approve a school representative account.

    This endpoint approves a school representative account by changing its status to active.

    Parameters:
        - user_id (int): The ID of the user to approve.
        - auth (Depends): The authentication token.
        - _ (Depends): The request context.

    Returns:
        GenericResponseModel: A GenericResponseModel containing the result of the operation.
            The response model is UserModel.

    Responses:
        - 200: Successfully approved school representative account. The model is GenericResponseModel.
        - 401: Invalid authentication token. The model is GenericResponseModel.
        - 404: User not found. The model is GenericResponseModel.
        - 500: Internal Server Error. The model is GenericResponseModel.
    """
    response: GenericResponseModel = UserService.approve_user(user_id)
    return build_api_response(response)


@router.put(
    "/reject/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Reject a school representative account or organizer account",
    description="Reject a school representative account by changing its status to rejected.",
    responses={
        200: {
            "model": GenericResponseModel[UserModel],
            "description": "Successfully rejected school representative account",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
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
async def reject_user(
    user_id: int,
    reason: str = Query(..., description="Reason for rejection"),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Reject a school representative account.

    This endpoint rejects a school representative account by changing its status to rejected.

    Parameters:
        - user_id (int): The ID of the user to reject.
        - reason (str): The reason for rejection.
        - auth (Depends): The authentication token.
        - _ (Depends): The request context.

    Returns:
        GenericResponseModel: A GenericResponseModel containing the result of the operation.
            The response model is UserModel.

    Responses:
        - 200: Successfully rejected school representative account. The model is GenericResponseModel.
        - 401: Invalid authentication token. The model is GenericResponseModel.
        - 404: User not found. The model is GenericResponseModel.
        - 500: Internal Server Error. The model is GenericResponseModel.
    """
    response: GenericResponseModel = UserService.reject_user(user_id, reason)
    return build_api_response(response)


@router.get(
    "/organizers/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel,
    summary="Search organizers.",
    description="Search organizers with pagination, filtering, and sorting.",
    responses={
        200: {
            "model": GenericResponseModel[PaginationResponseDataModel[list[UserModel]]],
            "description": "Successful search of organizers",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid authentication token",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
)
async def search_organizers(
    current_page: int = Query(1, description="Page number of the results"),
    items_per_page: int = Query(10, description="Number of results per page"),
    filter_params: Optional[str] = Query(None, alias="filter_params"),
    sorting_params: Optional[str] = Query(None, alias="sorting_params"),
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Search organizers.

    This endpoint searches for organizers in the database. It supports pagination, filtering, and sorting.

    Parameters:
        - current_page (int): The page number of the results. Default is 1.
        - items_per_page (int): The number of results per page. Default is 10.
        - filter_params (Optional[str]): The filter parameters for the query.
        - sorting_params (Optional[str]): The sorting parameters for the query.
        - auth (Depends): The authentication token.
        - _ (Depends): The request context.

    Returns:
        GenericResponseModel: A GenericResponseModel containing the result of the operation.
            The response model is PaginationResponseDataModel[list[UserModel]].

    Responses:
        - 200: Successful search of organizers. The model is GenericResponseModel.
        - 401: Invalid authentication token. The model is GenericResponseModel.
        - 500: Internal Server Error. The model is GenericResponseModel.
    """
    # Parse filter_params and sorting_params
    filters = parse_json_params(filter_params) if filter_params else None
    sorting = parse_json_params(sorting_params) if sorting_params else None

    # Call the search_organizers method of the UserService class
    response: GenericResponseModel = UserService.search_organizers(
        current_page, items_per_page, filters, sorting
    )

    # Return the response after adding the request context
    return build_api_response(response)
