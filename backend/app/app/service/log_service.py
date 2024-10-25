from datetime import datetime
from pathlib import Path
from typing import List, Optional
import re
from app.logger import logger
from app.utils.response_messages import ResponseMessages
from fastapi import status
from app.models.response import GenericResponseModel, PaginationResponseDataModel
from app.context_manager import context_actor_user_data, context_id_api



class LogService:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir

    def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        path: Optional[str] = None,
        request_id: Optional[str] = None,
        min_duration: Optional[float] = None,
        current_page: int = 1,
        items_per_page: int = 10
    ) -> GenericResponseModel:
        try:
            logs = []
            log_files = self._get_log_files(start_date, end_date)

            for log_file in log_files:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        log_entry = self._parse_log_line(line)
                        if log_entry and self._matches_filters(
                            log_entry, user_id, path, request_id, min_duration
                        ):
                            logs.append(log_entry)

            # Sort logs by timestamp in descending order (newest first)
            logs.sort(key=lambda x: x['timestamp'], reverse=True)

            # Pagination logic
            total_count = len(logs)
            total_pages = (total_count + items_per_page - 1) // items_per_page
            start_index = (current_page - 1) * items_per_page
            paginated_logs = logs[start_index:start_index + items_per_page]

            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.MSG_SUCCESS_GET_LOGS,
                status_code=status.HTTP_200_OK,
                data=PaginationResponseDataModel(
                    current_page=current_page,
                    items_per_page=items_per_page,
                    total_pages=total_pages,
                    total_items=total_count,
                    items=paginated_logs,
                ),
            )
        except Exception as e:
            logger.error(f"Error retrieving logs: {str(e)}")
            return GenericResponseModel(
                api_id=context_id_api.get(),
                message=ResponseMessages.ERR_INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data=None,
            )

    def _get_log_files(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Path]:
        today = datetime.now().date()
        all_logs = []

        # Always check current day's log first
        current_log = self.log_dir / "all.log"
        if current_log.exists():
            # For the current log file, we'll check the date filters
            if not start_date or start_date.date() <= today:
                if not end_date or end_date.date() >= today:
                    all_logs.append(current_log)

        # Get historical logs
        historical_logs = list(self.log_dir.glob("all.log.*"))

        if not (start_date or end_date):
            all_logs.extend(historical_logs)
            return all_logs

        # Filter historical logs
        for log_file in historical_logs:
            file_date = self._extract_date_from_filename(log_file.name)
            if file_date:
                if start_date and end_date:
                    if start_date.date() <= file_date <= end_date.date():
                        all_logs.append(log_file)
                elif start_date and file_date >= start_date.date():
                    all_logs.append(log_file)
                elif end_date and file_date <= end_date.date():
                    all_logs.append(log_file)

        return all_logs

    def _parse_log_line(self, line: str) -> Optional[dict]:
        try:
            pattern = r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+loglevel=(?P<level>\w+)\s+logger=(?P<logger>\S+)\s+(?P<function>\S+)\(\)\sL(?P<line>\d+)\s+(?P<message>.*)'
            match = re.match(pattern, line)
            
            if match:
                data = match.groupdict()
                
                # List of system functions to ignore
                system_functions = {
                    'build_api_response',
                    'dispatch',
                    '<module>',
                    'build_request_context',
                    'get_database_engine'
                }
                
                # Skip if it's a system function
                if data['function'] in system_functions:
                    return None
                    
                # Extract user ID from both patterns
                user_pattern1 = r'user_id=(\d+)'
                user_pattern2 = r'user ID (\d+)'
                
                user_match = re.search(user_pattern1, data['message'])
                if not user_match:
                    user_match = re.search(user_pattern2, data['message'])
                
                if user_match:
                    data['user_id'] = int(user_match.group(1))
                
                return data
            
            return None
        except Exception as e:
            logger.error(f"Error parsing log line: {e}")
            return None

    def _matches_filters(
        self,
        log_entry: dict,
        user_id: Optional[int],
        path: Optional[str],
        request_id: Optional[str],
        min_duration: Optional[float]
    ) -> bool:
        if user_id and ('user_id' not in log_entry or log_entry['user_id'] != user_id):
            return False
        
        if path and ('path' not in log_entry or path not in log_entry['path']):
            return False
        
        if request_id and ('request_id' not in log_entry or request_id != log_entry['request_id']):
            return False
        
        if min_duration and ('duration' not in log_entry or float(log_entry['duration']) < min_duration):
            return False
        
        return True

    @staticmethod
    def _extract_date_from_filename(filename: str) -> Optional[datetime.date]:
        pattern = r'all\.log\.(\d{4}-\d{2}-\d{2})'
        match = re.search(pattern, filename)
        if match:
            return datetime.strptime(match.group(1), '%Y-%m-%d').date()
        return None