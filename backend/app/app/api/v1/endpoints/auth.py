from datetime import datetime, timedelta

from app.context_manager import (
    build_request_context,
    context_actor_user_data,
    context_id_api,
    context_set_db_session_rollback,
)
from app.core.config import settings
from app.data_adapter.user import User
from app.dependencies import (
    authenticate_user_token,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.logger import logger
from app.models.response import (
    GenericResponseModel,
    OAuth2TokenModel,
    build_api_response,
)
from app.models.user import UserModel, UserStatus
from app.utils.exceptions import CustomAccountLockedException, CustomBadRequestException
from app.utils.response_messages import ResponseMessages
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.service.user_service import UserService

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post(
    "/login_user/",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": OAuth2TokenModel,
            "description": "Successful login",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid user credentials",
        },
        403: {
            "model": GenericResponseModel,
            "description": "Account locked",
        },
        500: {
            "model": GenericResponseModel,
            "description": "Internal Server Error",
        },
    },
    summary="Login User",
    description="Logs in user using form_data.",
    response_description="An access token, a refresh token and token type.",
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    _=Depends(build_request_context),
):
    """
    Login user
    :param form_data: OAuth2PasswordRequestForm contains username and password
    :param _: build_request_context dependency injection handles the request context
    :return: OAuth2TokenModel or GenericResponseModel
    """

    


    user = User.get_user_object_by_email(form_data.username)
    if user is None:
        context_set_db_session_rollback.set(True)
        return build_api_response(
            GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_401_UNAUTHORIZED,
                error=ResponseMessages.ERR_INVALID_USER_CREDENTIALS,
            )
        )
    
    try:
        UserService.check_account_lock(user)
    except CustomAccountLockedException as e:
        return build_api_response(
            GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=e.status_code,
                error=e.detail,
            )
        )
    
    
    if user.status == UserStatus.INACTIVE:
        return build_api_response(
            GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_403_FORBIDDEN,
                error=ResponseMessages.ERR_ACCOUNT_PENDING_APPROVAL,
            )
        )


    if not verify_password(form_data.password, user.password_hash):
        User.handle_failed_login(user.user_id)
        logger.info(
            msg=f"Invalid credentials for user {user.user_id} at {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        )
        context_set_db_session_rollback.set(True)
        return build_api_response(
            GenericResponseModel(
                api_id=context_id_api.get(),
                status_code=status.HTTP_401_UNAUTHORIZED,
                error=ResponseMessages.ERR_INVALID_USER_CREDENTIALS,
            )
        )

    # Reset failed login attempts on successful login
    User.reset_failed_login_attempts(user.user_id)

    # Generate access and refresh tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.build_user_token_data().model_dump(),
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        user.build_user_token_data().model_dump(),
        expires_delta=refresh_token_expires,
    )
    logger.info(
        msg=f"Login successful for user {user.user_id} at {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} with token {access_token}",
    )

    #  return token to client for further use
    return OAuth2TokenModel(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh_token",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "model": OAuth2TokenModel,
            "description": "Successful refresh token",
        },
        401: {
            "model": GenericResponseModel,
            "description": "Invalid refresh token",
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
    summary="Refresh Token",
    description="Refresh token using refresh token.",
    response_description="An access token, a refresh token and token type.",
)
async def refresh_token(
    auth=Depends(authenticate_user_token),
    _=Depends(build_request_context),
):
    """
    Refresh token
    :param auth: authenticate_user_token dependency injection handles the authentication
    :param _: build_request_context dependency injection handles the request context
    :return: OAuth2TokenModel
    """
    context_user_data = context_actor_user_data.get()
    if not context_user_data:
        raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

    user_id = context_user_data.user_id
    user: UserModel = User.get_user_by_id(user_id)
    if not user:
        raise CustomBadRequestException(ResponseMessages.ERR_USER_NOT_FOUND)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.build_user_token_data().model_dump(),
        expires_delta=access_token_expires,
    )
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(
        user.build_user_token_data().model_dump(),
        expires_delta=refresh_token_expires,
    )
    logger.info(
        msg=f"Login successful for user {user_id} at {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} with token {access_token}",
    )
    return OAuth2TokenModel(
        access_token=access_token,
        refresh_token=refresh_token,
    )
