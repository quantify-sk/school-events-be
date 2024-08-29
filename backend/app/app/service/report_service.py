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
from typing import Any, List, Dict, Optional
from app.models.school import SchoolCreateModel, SchoolModel, SchoolUpdateModel
from app.data_adapter.report import Report, ReportType
from app.models.report import ReportFilters


class ReportService:
    @staticmethod
    def generate_report(
        report_type: str, filters: ReportFilters
    ) -> GenericResponseModel:
        try:
            report_data = None
            if report_type == ReportType.EVENT_SUMMARY.value:
                report_data = Report.generate_event_summary(filters.dict())
            elif report_type == ReportType.ATTENDANCE.value:
                report_data = Report.generate_attendance_report(filters.dict())
            elif report_type == ReportType.RESERVATION.value:
                report_data = Report.generate_reservation_report(filters.dict())
            # Add more report types as needed

            report = Report.create_report(
                report_type=ReportType(report_type),
                generated_by=filters.user_id,
                filters=filters.dict(),
                data=report_data,
            )

            logger.info(
                f"Generated report of type {report_type} for user ID: {filters.user_id}"
            )
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GENERATE_REPORT,
                status_code=status.HTTP_200_OK,
                data=report,
            )

        except Exception as e:
            logger.error(
                f"Unexpected error generating report. Type: {report_type}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_report_by_id(report_id: int) -> GenericResponseModel:
        try:
            report = Report.get_report_by_id(report_id)
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_REPORT,
                status_code=status.HTTP_200_OK,
                data=report,
            )
        except CustomBadRequestException as e:
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected error getting report. ID: {report_id}. Error: {str(e)}"
            )
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)

    @staticmethod
    def get_all_reports() -> GenericResponseModel:
        try:
            reports = Report.get_all_reports()
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_ALL_REPORTS,
                status_code=status.HTTP_200_OK,
                data=reports,
            )
        except Exception as e:
            logger.error(f"Unexpected error getting all reports. Error: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INTERNAL_SERVER_ERROR)
