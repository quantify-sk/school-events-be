import math
from datetime import datetime
from typing import Dict, List, Optional

from app.context_manager import context_actor_user_data, context_id_api
from app.data_adapter.notification import Notification
from app.data_adapter.user import User
from app.logger import logger
from app.models.notification import NotificationType
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.models.user import UserCreateModel, UserModel, UserUpdateModel
from app.utils.exceptions import (
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.utils.response_messages import ResponseMessages
from fastapi import status


class UserService:
    @staticmethod
    def create_user(
        user_data: UserCreateModel,  # Data of the new user
    ) -> GenericResponseModel:
        """
        Create a new user.

        Args:
            user_data (UserCreateModel): Data of the new user.

        Returns:
            GenericResponseModel: A GenericResponseModel with the created user or an error.

        Raises:
            CustomInternalServerErrorException: If an error occur while creating the user.
        """
        # Check if the user is authenticated
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Check if the email is already taken
        user = User.get_user_by_email(user_data.user_email)

        # Return an error if the email is already taken
        if user:
            raise CustomBadRequestException(ResponseMessages.ERR_EMAIL_ALREADY_TAKEN)

        # Create a new user
        new_user = User.create_new_user(
            user_data,
        )

        # Raise an exception if an error occur while creating the user
        if not new_user:
            logger.error(
                f"Error while creating user for user ID {context_actor_user_data.get().user_id}"
            )
            raise CustomInternalServerErrorException()

        # Log the successful creation of the new user
        logger.info(
            f"User ID {context_actor_user_data.get().user_id} created successfully new user: {new_user.user_id}"
        )

        # Create a new notification
        Notification.create_notification(
            f"Uživatel {new_user.first_name} {new_user.last_name} byl úspěšně vytvořen",
            datetime.now().date(),
            NotificationType.INFO,
            [context_actor_user_data.get().user_id],
        )

        # Get the user from the database
        new_user = User.get_user_by_id(new_user.user_id)

        # Raise an exception if an error occur while getting the user
        if not new_user:
            raise CustomInternalServerErrorException()

        # Return a GenericResponseModel with the created user
        return GenericResponseModel(
            api_id=context_id_api.get(),  # The ID of the API
            message=ResponseMessages.MSG_SUCCESS_CREATE_USER,  # The success message
            status_code=status.HTTP_200_OK,  # The success status code
            data=new_user,  # The created user
        )

    @staticmethod
    def get_all_users(
        current_page: int,
        items_per_page: int,
        filter_params: Optional[List[Dict[str, str]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> GenericResponseModel:
        """
        Get all users.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filters (dict): The filters to apply.

        Returns:
            GenericResponseModel: A GenericResponseModel with the list of users or an error.
        """
        # Check if the user is authenticated
        if not context_actor_user_data.get():
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Get all users
        users, total_items = User.get_users(
            current_page,
            items_per_page,
            filter_params,
            sorting_params,
        )

        total_pages = math.ceil(total_items / items_per_page)

        # Return a GenericResponseModel with the list of users
        return GenericResponseModel(
            api_id=context_id_api.get(),  # The ID of the API
            message=ResponseMessages.MSG_SUCCESS_GET_ALL_USERS,  # The success message
            status_code=status.HTTP_200_OK,  # The success status code
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_items,
                items=users,
            ),
        )

    @staticmethod
    def delete_user(
        user_id: int,  # The ID of the user deleting another user.
    ) -> GenericResponseModel:  # The response containing the result of the operation.
        """
        Delete a user by ID.

        Args:
            user_id (int): The ID of the user to be deleted.

        Returns:
            GenericResponseModel: The response containing the result of the operation.
        """
        # Check if the user deleting another user is authenticated
        if not context_actor_user_data.get():
            raise CustomInternalServerErrorException()

        # Get the user deleting another user
        user = User.delete_user_by_id(user_id)
        if not user:
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Log the successful deletion of the user
        logger.info(f"User ID {user_id} deleted user ID {user_id}")

        return GenericResponseModel(
            api_id=context_id_api.get(),  # The ID of the API
            message=ResponseMessages.MSG_SUCCESS_DELETE_USER,  # The success message
            status_code=status.HTTP_200_OK,  # The success status code
            data=user,  # The deleted user
        )

    @staticmethod
    def update_user(
        user_id: int,  # The ID of the user updating another user.
        user_data: UserUpdateModel,  # The updated user data.
    ) -> GenericResponseModel:  # The response containing the result of the operation.
        """
        Update a user by ID.

        Args:
            user_id (int): The ID of the user to be updated.
            user_data (UserUpdateModel): The updated user data.

        Returns:
            GenericResponseModel: The response containing the result of the operation.
        """
        # Check if the user is authenticated
        if not context_actor_user_data.get():
            raise CustomInternalServerErrorException()

        if not User.get_user_by_id(user_id):
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Check if the email is already taken
        existing_user = User.get_user_by_email(user_data.user_email)
        if existing_user and existing_user.user_id != user_id:
            raise CustomBadRequestException(ResponseMessages.ERR_EMAIL_ALREADY_TAKEN)

        # Perform the user update
        updated_user = User.update_user_by_id(user_id, user_data)
        if not updated_user:
            raise CustomInternalServerErrorException()

        # Manage roles and permissions, assuming roles and permissions are handled by separate functions
        user = User.get_user_by_id(user_id)
        if not user:
            raise CustomInternalServerErrorException()

        # Log the successful update of the user
        logger.info(f"Successfully updated user ID {user_id}")
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_UPDATE_USER,
            status_code=status.HTTP_200_OK,
            data=user,
        )

    @staticmethod
    def get_user_by_id(
        user_id: int,  # The ID of the user to retrieve.
    ) -> UserModel:  # The retrieved user.
        """
        Get a user by ID.

        Args:
            user_id (int): The ID of the user to retrieve.

        Returns:
            UserModel: The retrieved user.

        Raises:
            CustomBadRequestException: If the user does not exist in the database.
        """
        # Get the user from the database
        user = User.get_user_by_id(user_id)

        # Raise an exception if the user does not exist
        if not user:
            raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

        # Log the successful retrieval of the user
        logger.info(f"Successfully retrieved user ID {user_id}")

        # Return the user
        return GenericResponseModel(
            api_id=context_id_api.get(),  # The ID of the API
            message=ResponseMessages.MSG_SUCCESS_GET_USER,  # The success message
            status_code=status.HTTP_200_OK,  # The success status code
            data=user,  # The retrieved user
        )
