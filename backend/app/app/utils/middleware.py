import base64
import secrets
import uuid
from datetime import datetime
from typing import Callable, Optional

from app.core.config import settings
from app.logger import logger
from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Middleware for logging request and response
class RequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        analytical_request_id = str(uuid.uuid4())
        start_time = datetime.now()
        logger.info(
            f"Request {analytical_request_id} started for path: {request.url.path}"
        )

        response = await call_next(request)

        duration = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Request {analytical_request_id} ended for path: {request.url.path}. Duration: {duration:.2f} ms"
        )
        return response


class BaseAuthMiddleware(BaseHTTPMiddleware):
    def unauthorized(self, realm: Optional[str] = None) -> Response:
        response = Response("Unauthorized", status_code=401)
        if realm:
            response.headers["WWW-Authenticate"] = f'Basic realm="{realm}"'
        return response


class FilesAuthMiddleware(BaseAuthMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/files/"):
            token = request.query_params.get("token")
            if not token:
                logger.warning("Token missing in request to files endpoint.")
                return self.unauthorized()

            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                )
                file_path = payload.get("file_path")
                if not file_path or not request.url.path.endswith(file_path):
                    logger.warning("Invalid or mismatched file path in token.")
                    return self.unauthorized()
            except JWTError as e:
                logger.error(f"JWT decoding error for files: {e}")
                return self.unauthorized()

        return await call_next(request)


class ApidocBasicAuthMiddleware(BaseAuthMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return self.unauthorized(realm="Access to the API docs")
            try:
                scheme, credentials = auth_header.split()
                if scheme.lower() != "basic":
                    return self.unauthorized(realm="Access to the API docs")
                decoded = base64.b64decode(credentials).decode("ascii")
                username, password = decoded.split(":")
                if secrets.compare_digest(
                    username, settings.API_LOGIN
                ) and secrets.compare_digest(password, settings.API_PASSWORD):
                    return await call_next(request)
            except (ValueError, base64.binascii.Error) as e:
                logger.error(f"Error parsing authorization header: {e}")
                return self.unauthorized(realm="Access to the API docs")

        return await call_next(request)
