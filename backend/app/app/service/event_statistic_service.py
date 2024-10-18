from app.utils.response_messages import ResponseMessages
from app.utils.exceptions import CustomBadRequestException
from app.models.response import GenericResponseModel
from app.models.statistics import StatisticsRequestModel, StatisticsResponseModel
from app.data_adapter.event import Event
from fastapi import status
from app.context_manager import context_id_api, context_actor_user_data
from app.logger import logger
from app.models.report import ReportType


class EventStatisticsService:
    @staticmethod
    def get_event_statistics(
        filters: StatisticsRequestModel, report_type: ReportType
    ) -> GenericResponseModel:
        try:
            # Generate only the required statistics based on report_type
            statistics = Event.generate_statistics(filters, report_type)

            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_STATISTICS,
                status_code=status.HTTP_200_OK,
                data=StatisticsResponseModel(**statistics),
            )

        except Exception as e:
            logger.error(f"Error generating statistics: {str(e)}")
            raise CustomBadRequestException(ResponseMessages.ERR_GENERATING_STATISTICS)
