from datetime import datetime
from fastapi import HTTPException, status
from pytz import timezone


class CustomAuthException(HTTPException):
    """Exception for invalid authentication credentials."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


class CustomInternalServerErrorException(HTTPException):
    """Exception for internal server errors."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


class CustomBadRequestException(HTTPException):
    """Exception for general not found cases."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class CustomValidationException(HTTPException):
    """Exception for Pydantic validation errors."""

    def __init__(self, errors: list) -> None:
        messages = [error["msg"] for error in errors]
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(messages[0])
        )


class CustomAccountLockedException(HTTPException):
    """Exception for locked user accounts."""

    def __init__(self, unlock_time: datetime) -> None:
        slovakia_tz = timezone("Europe/Bratislava")
        local_time = unlock_time.astimezone(slovakia_tz)
        formatted_time = local_time.strftime("%d.%m.%Y %H:%M:%S")
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked. Please try again after {formatted_time}.",
        )
