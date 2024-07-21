from datetime import datetime
from typing import Dict, List, Optional

from app.database import Base
from app.models.get_params import ParameterValidator
from app.models.log import LogModel
from app.models.user import UserModel
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String


class Log(Base):
    __tablename__ = "log"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    table_name = Column(String(255), nullable=False)
    table_primary_key = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)

    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)

    def __init__(
        self,
        user_id: int | None,
        table_name: str,
        table_primary_key: int,
        old_data: dict | None,
        new_data: dict | None,
    ):
        self.user_id = user_id
        self.table_name = table_name
        self.table_primary_key = table_primary_key
        self.old_data = old_data
        self.new_data = new_data

    def _to_model(self):
        from app.data_adapter.user import User

        user = User.get_user_by_id(self.user_id) if self.user_id else None
        return LogModel(
            log_id=self.log_id,
            user_id=self.user_id,
            timestamp=self.timestamp,
            table_name=self.table_name,
            table_primary_key=self.table_primary_key,
            old_data=self.old_data,
            new_data=self.new_data,
            user=UserModel(**user.model_dump()) if user else None,
        )

    @classmethod
    def get_logs(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[List[Dict[str, str]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> tuple[List[UserModel], int]:
        """
        Get logs by filters.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[List[Dict[str, str]]]): The filter parameters.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters.

        Returns:
            List[LogModel]: The list of logs if found, otherwise an empty list.
            int: Total count of logs matching the filter criteria.
        """
        from app.context_manager import get_db_session

        # Get logs
        db = get_db_session()
        query = db.query(Log)

        query = ParameterValidator.apply_filters_and_sorting(
            query,
            Log,
            filter_params,
            sorting_params,
        )

        total_count = query.count()
        logs = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [log._to_model() for log in logs], total_count

    @classmethod
    def get_table_changelog(
        cls,
        form_id: int,
        from_datetime: datetime,
        to_datetime: datetime,
        table_name: str,
    ) -> List[LogModel]:
        from app.context_manager import get_db_session

        db = get_db_session()
        logs = (
            db.query(Log)
            .filter(Log.timestamp.between(from_datetime, to_datetime))
            .filter(Log.table_primary_key == form_id)
            .filter(Log.table_name == table_name)
            .all()
        )

        return [log._to_model() for log in logs]
