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
from app.models.statistics import StatisticsRequestModel, StatisticsResponseModel
from app.service.event_statistic_service import EventStatisticsService

router = APIRouter()


@router.post(
    "/statistics",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[StatisticsResponseModel],
    summary="Get event statistics",
    description="Generate comprehensive event statistics based on provided filters.",
    responses={
        200: {
            "model": GenericResponseModel[StatisticsResponseModel],
            "description": "Successful retrieval of event statistics",
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
async def get_event_statistics(
    filters: StatisticsRequestModel,
    _=Depends(build_request_context),
) -> GenericResponseModel:
    """
    Generate comprehensive event statistics based on provided filters.
    """
    response: GenericResponseModel = EventStatisticsService.get_event_statistics(
        filters
    )
    return build_api_response(response)
