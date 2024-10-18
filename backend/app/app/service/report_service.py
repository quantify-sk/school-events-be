from http.client import HTTPException
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
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from fastapi.responses import StreamingResponse
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter, landscape
from app.service.event_statistic_service import EventStatisticsService
from app.models.statistics import StatisticsRequestModel


class ReportService:
    @staticmethod
    def generate_report(
        report_type: str, filters: ReportFilters
    ) -> GenericResponseModel:
        try:
            report_data = None
            if report_type in [
                ReportType.EVENT_SUMMARY.value,
                ReportType.ATTENDANCE.value,
                ReportType.RESERVATION.value,
            ]:
                # Use EventStatisticsService for event-related reports
                statistics_filters = StatisticsRequestModel(**filters.dict())
                response = EventStatisticsService.get_event_statistics(
                    statistics_filters, report_type
                )
                report_data = response.data.dict()
            # Add more report types as needed

            # Create the report
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

        except ValueError as e:
            logger.error(f"Invalid input for report generation: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_INVALID_REPORT_INPUT)
        except Exception as e:
            logger.error(f"Unexpected error generating report: {str(e)}")
            raise CustomInternalServerErrorException()

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

    @staticmethod
    def save_report(report_data: Dict[str, Any]) -> GenericResponseModel:
        try:
            user_id = context_actor_user_data.get().user_id
            report = Report.create_report(
                report_type=ReportType(report_data["report_type"]),
                generated_by=user_id,
                filters=report_data.get("filters", {}),
                data=report_data["data"],
            )
            logger.info(f"Saved report for user ID: {user_id}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_SAVE_REPORT,
                status_code=status.HTTP_200_OK,
                data=report,
            )
        except Exception as e:
            logger.error(f"Unexpected error saving report. Error: {str(e)}")
            raise CustomInternalServerErrorException(
                ResponseMessages.ERR_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    async def email_report(report_data: Dict[str, Any]):
        try:
            # This method should be implemented to send an email with the report
            # You might want to use an email service or library here
            # For now, we'll just log the action
            user_id = context_actor_user_data.get().user_id
            logger.info(f"Emailing report for user ID: {user_id}")
            # Implement email sending logic here
            # ...
        except Exception as e:
            logger.error(f"Unexpected error emailing report. Error: {str(e)}")
            # Since this is a background task, we'll log the error but not raise an exception

    @staticmethod
    def export_report(report_data: Dict[str, Any], format: str) -> StreamingResponse:
        try:
            user_id = context_actor_user_data.get().user_id
            logger.info(f"Exporting report in {format} format for user ID: {user_id}")

            # Convert report_data to a pandas DataFrame
            df = pd.DataFrame(report_data.get("data", []))

            if df.empty:
                raise ValueError("No data to export")

            if format == "csv":
                # Generate CSV with UTF-8 encoding and BOM
                output = io.StringIO()
                df.to_csv(output, index=False, encoding="utf-8-sig")
                output.seek(0)

                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=report.csv"},
                )

            elif format == "excel":
                # Generate Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Report", index=False)
                output.seek(0)

                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename=report.xlsx"
                    },
                )

            elif format == "pdf":
                # Generate PDF
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=landscape(letter),
                    rightMargin=30,
                    leftMargin=30,
                    topMargin=30,
                    bottomMargin=30,
                )
                elements = []

                styles = getSampleStyleSheet()
                title = Paragraph("Report", styles["Title"])
                elements.append(title)

                # Split the DataFrame into chunks of 10 columns each
                chunk_size = 10
                for i in range(0, len(df.columns), chunk_size):
                    chunk = df.iloc[:, i : i + chunk_size]

                    # Convert DataFrame chunk to a list of lists for the PDF table
                    data = [chunk.columns.tolist()] + chunk.values.tolist()

                    # Ensure all data is string type
                    data = [[str(cell) for cell in row] for row in data]

                    table = Table(data, repeatRows=1)
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 8),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                                ("FONTSIZE", (0, 1), (-1, -1), 7),
                                ("TOPPADDING", (0, 1), (-1, -1), 6),
                                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ]
                        )
                    )
                    elements.append(table)
                    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

                doc.build(elements)
                buffer.seek(0)

                return StreamingResponse(
                    iter([buffer.getvalue()]),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=report.pdf"},
                )

            else:
                raise ValueError(f"Unsupported format: {format}")

        except ValueError as ve:
            logger.error(f"ValueError in export_report: {str(ve)}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Unexpected error exporting report. Error: {str(e)}")
            raise CustomInternalServerErrorException()

    @staticmethod
    def delete_report(report_id: int) -> GenericResponseModel:
        try:
            Report.delete_report(report_id)
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_DELETE_REPORT,
                status_code=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Unexpected error deleting report: {str(e)}")
            raise CustomInternalServerErrorException()
