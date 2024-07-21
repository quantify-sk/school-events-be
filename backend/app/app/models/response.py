import uuid
from enum import Enum
from typing import Generic, Optional, TypeVar

from app.logger import logger
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

# Define a type variable that can be any type
DataT = TypeVar("DataT")


class PaginationResponseDataModel(BaseModel, Generic[DataT]):
    """Pagination response model"""

    current_page: int
    items_per_page: int
    total_pages: int
    total_items: int
    items: Optional[DataT]


class GenericResponseModel(BaseModel, Generic[DataT]):
    """Generic response model for all responses, capable of handling dynamic data types."""

    api_id: Optional[str] = Field(description="API identifier")
    error: Optional[str] = Field(None, description="Error message, if any")
    message: Optional[str] = Field(
        None, description="General message or response status"
    )
    data: Optional[DataT] = Field(None, description="Dynamically typed data field")
    status_code: int = Field(description="HTTP status code of the response")
    unread_notification: bool = Field(
        False, description="Flag to indicate new notifications for the user"
    )


class TokenType(str, Enum):
    bearer = "bearer"


class OAuth2TokenModel(BaseModel):
    """OAuth2 token model"""

    access_token: str
    refresh_token: str
    token_type: TokenType = TokenType.bearer


def build_api_response(
    generic_response: GenericResponseModel,
) -> ORJSONResponse:
    """Build API response"""
    from app.context_manager import context_log_meta

    try:
        if not generic_response.api_id:
            generic_response.api_id = str(uuid.uuid4())
        if not generic_response.status_code:
            generic_response.status_code = (
                status.HTTP_200_OK
                if not generic_response.error
                else status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        # Set unread_notification from the context log meta
        generic_response.unread_notification = context_log_meta.get().get(
            "unread_notification", False
        )

        response_json = jsonable_encoder(generic_response)
        res = ORJSONResponse(
            status_code=generic_response.status_code,
            content=response_json,
        )
        logger.info(
            msg="build_api_response: Generated Response with status_code:"
            + f"{generic_response.status_code} api_id: {generic_response.api_id} unread_notification: {generic_response.unread_notification}",
        )
        return res
    except Exception as e:
        logger.error(
            msg=f"exception in build_api_response error: {e}",
        )
        return ORJSONResponse(
            status_code=generic_response.status_code,
            content=generic_response.error,
        )
