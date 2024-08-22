import math
from datetime import datetime, timedelta
import typing

from app.context_manager import context_actor_user_data, context_id_api
from app.data_adapter.notification import Notification
from app.data_adapter.user import User
from app.logger import logger
from app.models.notification import NotificationType
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.models.user import (
    UserCreateModel,
    UserModel,
    UserRole,
    UserStatus,
    UserUpdateModel,
)
from app.utils.exceptions import (
    CustomAccountLockedException,
    CustomBadRequestException,
    CustomInternalServerErrorException,
)
from app.utils.response_messages import ResponseMessages
from fastapi import status
from app.data_adapter.school import School
from typing import List, Dict, Optional


class UserService:
    @staticmethod
    def create_user(user_data: UserCreateModel) -> GenericResponseModel:
        """
        Create a new user, handling school representatives separately.

        This method performs the following steps:
        1. Checks if the email is already taken
        2. For school representatives:
           - Validates school data
           - Checks for existing school or creates a new one
           - Associates the school with the user
        3. Creates the new user
        4. Creates a notification for the new user

        Args:
            user_data (UserCreateModel): The data for creating the new user.

        Returns:
            GenericResponseModel: A response model containing the created user data or error information.

        Raises:
            CustomBadRequestException: If the email is already taken or school data is missing for representatives.
            CustomInternalServerErrorException: If there's an unexpected error during user creation.
        """
        try:
            # Check if the email is already taken
            existing_user = User.get_user_by_email(user_data.user_email)
            if existing_user:
                raise CustomBadRequestException(
                    ResponseMessages.ERR_EMAIL_ALREADY_TAKEN
                )

            # Handle school representative case
            if user_data.role == UserRole.SCHOOL_REPRESENTATIVE:
                if not user_data.school:
                    raise CustomBadRequestException(
                        ResponseMessages.ERR_MISSING_SCHOOL_DATA
                    )

                # Check if the school already exists
                existing_school = School.get_school_by_ico(user_data.school.ico)
                if existing_school:
                    school = existing_school
                else:
                    # Create a new school
                    school = School.create_new_school(user_data.school)

                # Associate the school with the user data
                user_data.school_id = school.id

            # Create a new user
            new_user = User.create_new_user(user_data)

            # Create a new notification
            Notification.create_notification(
                f"Uživatel {new_user.first_name} {new_user.last_name} byl úspěšně vytvořen",
                datetime.now().date(),
                NotificationType.INFO,
                [new_user.user_id],
            )

            # Return a GenericResponseModel with the created user
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_CREATE_USER,
                status_code=status.HTTP_200_OK,
                data=new_user,
            )

        except CustomBadRequestException as e:
            raise e
        except Exception as e:
            logger.error(f"Error while creating user: {str(e)}")
            raise CustomInternalServerErrorException()

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

    @staticmethod
    def check_account_lock(user: User) -> None:
        """
        Check if the user account is locked and raise an exception if it is.

        Args:
            user (User): The user to check.

        Raises:
            CustomAccountLockedException: If the account is locked.
        """
        is_locked, unlock_time = user.is_account_locked()
        if is_locked:
            raise CustomAccountLockedException(unlock_time)

    @staticmethod
    def handle_failed_login(user: User) -> None:
        """
        Handle a failed login attempt.

        Args:
            user (User): The user who failed to log in.
        """
        User.handle_failed_login(user.user_id)

    @staticmethod
    def reset_failed_login_attempts(user: User) -> None:
        """
        Reset failed login attempts for a user.

        Args:
            user (User): The user to reset failed login attempts for.
        """
        User.reset_failed_login_attempts(user.user_id)

    @staticmethod
    def get_user_role(user_id: int) -> GenericResponseModel:
        """
        Get the role of a user by their ID.

        This method fetches the user's role from the database and returns it
        wrapped in a GenericResponseModel.

        Args:
            user_id (int): The ID of the user whose role we want to retrieve.

        Returns:
            GenericResponseModel: A response model containing the user's role or an error message.
        """
        # Attempt to get the user's role from the database
        user_role = User.get_user_role(user_id)

        # If no role is found, return a 404 error
        if user_role is None:
            return GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_404_NOT_FOUND,
                error=ResponseMessages.ERR_USER_NOT_FOUND,
            )

        # If a role is found, return it in a success response
        return GenericResponseModel(
            api_id=context_id_api.get(),
            status_code=status.HTTP_200_OK,
            message=ResponseMessages.MSG_SUCCESS_GET_USER_ROLE,
            data={"role": user_role},
        )

    @staticmethod
    def get_pending_approval_requests(
        current_page: int,
        items_per_page: int,
        filter_params: Optional[List[Dict[str, str]]] = None,
        sorting_params: Optional[List[Dict[str, str]]] = None,
    ) -> GenericResponseModel:
        """
        Get all users with pending approval status.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[List[Dict[str, str]]]): The filters to apply.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters to apply.

        Returns:
            GenericResponseModel: A GenericResponseModel with the list of pending users or an error.
        """
        # Get pending approval users
        pending_users, total_items = User.get_users_by_status(
            UserStatus.INACTIVE,
            current_page,
            items_per_page,
            filter_params,
            sorting_params,
        )

        total_pages = math.ceil(total_items / items_per_page)

        # Return a GenericResponseModel with the list of pending users
        return GenericResponseModel(
            api_id=context_id_api.get(),
            message=ResponseMessages.MSG_SUCCESS_GET_PENDING_USERS,
            status_code=status.HTTP_200_OK,
            data=PaginationResponseDataModel(
                current_page=current_page,
                items_per_page=items_per_page,
                total_pages=total_pages,
                total_items=total_items,
                items=pending_users,
            ),
        )

    @staticmethod
    def approve_user(user_id: int) -> GenericResponseModel:
        """
        Approve a school representative account.

        This method changes the status of a user from PENDING_APPROVAL to ACTIVE.

        Args:
            user_id (int): The ID of the user to approve.

        Returns:
            GenericResponseModel: A response model containing the result of the operation.
        """
        logger.info(f"Approving school representative with ID: {user_id}")
        user = User.approve_user(user_id)

        if user:
            logger.info(
                f"Successfully approved school representative: {user.user_email}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_200_OK,
                message=ResponseMessages.MSG_SUCCESS_APPROVE_USER,
                data=user,
            )
        else:
            logger.warning(f"User with ID {user_id} not found for approval")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_404_NOT_FOUND,
                error=ResponseMessages.ERR_USER_NOT_FOUND,
            )

    @staticmethod
    def reject_user(user_id: int, reason: str) -> GenericResponseModel:
        """
        Reject a school representative account.

        This method changes the status of a user from PENDING_APPROVAL to REJECTED.

        Args:
            user_id (int): The ID of the user to reject.
            reason (str): The reason for rejection.

        Returns:
            GenericResponseModel: A response model containing the result of the operation.
        """
        logger.info(f"Rejecting school representative with ID: {user_id}")
        user = User.update_user_status(user_id, UserStatus.REJECTED, reason)

        if user:
            logger.info(
                f"Successfully rejected school representative: {user.user_email}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_200_OK,
                message=ResponseMessages.MSG_SUCCESS_REJECT_USER,
                data=user,
            )
        else:
            logger.warning(f"User with ID {user_id} not found for rejection")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_404_NOT_FOUND,
                error=ResponseMessages.ERR_USER_NOT_FOUND,
            )
