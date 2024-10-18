import fastapi.responses
from http.client import HTTPException
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
import app.context_manager
from typing import Any, Optional, List, Dict, Union
from pydantic import Json
from app.utils.exceptions import CustomBadRequestException
from app.logger import logger
from pydantic import ValidationError
from app.service.report_service import ReportService
from app.models.report import ReportFilters, ReportModel, ReportResponse
from fastapi.responses import StreamingResponse
from app.context_manager import build_request_context

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
        200: {
            "model": List[ReportModel],
            "description": "Successfully retrieved all reports",
        },
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


@router.post(
    "/save",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Save a generated report",
    description="Save a generated report to the database.",
    responses={
        200: {"model": ReportResponse, "description": "Successfully saved report"},
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def save_report(
    report_data: Dict[str, Any],
    auth: dict = Depends(authenticate_user_token),
    _: None = Depends(build_request_context),
) -> ReportResponse:
    """
    Save a generated report to the database.

    This endpoint allows authenticated users to save a generated report to the database.

    Args:
        report_data (Dict[str, Any]): The report data to save.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        ReportResponse: The details of the saved report.

    Raises:
        HTTPException:
            - 500: If there's an internal server error during the process.
    """
    response = ReportService.save_report(report_data)
    return build_api_response(response)


# @router.post(
#     "/email",
#     response_model=GenericResponseModel,
#     status_code=status.HTTP_200_OK,
#     summary="Email a generated report",
#     description="Send a generated report via email.",
#     responses={
#         200: {"model": GenericResponseModel, "description": "Successfully sent report via email"},
#         500: {"model": GenericResponseModel, "description": "Internal Server Error"},
#     },
# )
# async def email_report(
#     report_data: Dict[str, Any],
#     background_tasks: BackgroundTasks,
#     auth: dict = Depends(authenticate_user_token),
#     _: None = Depends(build_request_context),
# ) -> GenericResponseModel:
#     """
#     Send a generated report via email.

#     This endpoint allows authenticated users to send a generated report via email.

#     Args:
#         report_data (Dict[str, Any]): The report data to send.
#         background_tasks (BackgroundTasks): The background task manager.
#         auth (dict): The authenticated user's information (injected by dependency).
#         _ (None): Placeholder for request context building (injected by dependency).

#     Returns:
#         GenericResponseModel: A response indicating that the email task has been queued.

#     Raises:
#         HTTPException:
#             - 500: If there's an internal server error during the process.
#     """

#     background_tasks.add_task(ReportService.email_report, report_data, auth['user_id'])
#     return build_api_response({"message": "Report email task has been queued"})


@router.post(
    "/export/{format}",
    response_model=GenericResponseModel,
    status_code=status.HTTP_200_OK,
    summary="Export a generated report",
    description="Export a generated report in the specified format (PDF, Excel, CSV).",
    responses={
        200: {
            "model": GenericResponseModel,
            "description": "Successfully exported report",
        },
        500: {"model": GenericResponseModel, "description": "Internal Server Error"},
    },
)
async def export_report(
    format: str,
    report_data: Dict[str, Any],
    auth: dict = Depends(authenticate_user_token),
    _: None = Depends(build_request_context),
) -> StreamingResponse:
    """
    Export a generated report in the specified format (PDF, Excel, CSV).

    This endpoint allows authenticated users to export a generated report in the specified format.

    Args:
        format (str): The export format (PDF, Excel, CSV).
        report_data (Dict[str, Any]): The report data to export.
        auth (dict): The authenticated user's information (injected by dependency).
        _ (None): Placeholder for request context building (injected by dependency).

    Returns:
        GenericResponseModel: A response indicating that the report has been successfully exported.

    Raises:
        HTTPException:
            - 400: If the export format is invalid.
            - 500: If there's an internal server error during the process.
    """
    format = report_data.get("format", format)
    print("FORMAT: ", format)
    try:
        if format not in ["pdf", "excel", "csv"]:
            raise HTTPException(status_code=400, detail="Invalid export format")

        return ReportService.export_report(report_data, format)
    except Exception as e:
        logger.error(f"Unexpected error exporting report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
