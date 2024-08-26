import app.api.v1.endpoints
import app.logger
from datetime import datetime, timedelta
import json
from fastapi import APIRouter, Depends, Query, status, File, Form, UploadFile
from app.service.event_service import EventService
from app.models.response import GenericResponseModel, build_api_response
from app.models.event import (
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
from app.service.report_service import ReportService
from app.models.report import ReportFilters, ReportModel, ReportResponse

router = APIRouter()

@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a new report",
    description="Generate a new report based on the specified type and filters.",
    responses={
        200: {"model": ReportResponse, "description": "Successfully generated report"},
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def generate_report(
    filters: ReportFilters,
    auth: dict = Depends(authenticate_user_token),
    _: None = Depends(build_request_context),
) -> ReportResponse:
    """
    Generate a new report based on the provided filters and report type.

    This endpoint allows authenticated users to create a new report by specifying
    the report type and applying various filters such as date range and user ID.

    Args:
        filters (ReportFilters): The filters and report type for generating the report.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        ReportResponse: The generated report's details and metadata.

    Raises:
        HTTPException: 
            - 500: If there's an internal server error during the process.
    """
    response = ReportService.generate_report(filters.report_type, filters)
    return build_api_response(response)

@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get report by ID",
    description="Retrieve a report by its unique identifier.",
    responses={
        200: {"model": ReportResponse, "description": "Successfully retrieved report"},
        404: {"model": GenericResponseModel, "description": "Report not found"},
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def get_report(
    report_id: int,
    auth: dict = Depends(authenticate_user_token),
    _: None = Depends(build_request_context),
) -> ReportResponse:
    """
    Retrieve a specific report by its unique identifier.

    This endpoint allows authenticated users to fetch a report using its ID.

    Args:
        report_id (int): The unique identifier of the report to retrieve.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        ReportResponse: The details of the retrieved report.

    Raises:
        HTTPException: 
            - 404: If the report with the given ID is not found.
            - 500: If there's an internal server error during the process.
    """
    response = ReportService.get_report_by_id(report_id)
    return build_api_response(response)

@router.get(
    "/",
    response_model=List[ReportModel],
    status_code=status.HTTP_200_OK,
    summary="Get all reports",
    description="Retrieve a list of all available reports.",
    responses={
        200: {"model": List[ReportModel], "description": "Successfully retrieved all reports"},
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def get_all_reports(
    auth: dict = Depends(authenticate_user_token),
    _: None = Depends(build_request_context),
) -> List[ReportModel]:
    """
    Retrieve a list of all available reports in the system.

    This endpoint allows authenticated users to fetch all reports stored in the database.

    Args:
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        List[ReportModel]: A list containing all available reports.

    Raises:
        HTTPException: 
            - 500: If there's an internal server error during the process.
    """
    response = ReportService.get_all_reports()
    return build_api_response(response)