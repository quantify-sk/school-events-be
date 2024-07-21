from fastapi import HTTPException, status


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
