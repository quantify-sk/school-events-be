import base64
import secrets
import uuid
from datetime import datetime
from typing import Callable, Optional

from app.core.config import settings
from app.database import SessionLocal
from app.logger import logger
from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class BaseAuthMiddleware(BaseHTTPMiddleware):
    def unauthorized(self, realm: Optional[str] = None) -> Response:
        response = Response("Unauthorized", status_code=401)
        if realm:
            response.headers["WWW-Authenticate"] = f'Basic realm="{realm}"'
        return response


class CombinedAuthMiddleware(BaseAuthMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        try:
            if path.startswith("/files/"):
                token = request.query_params.get("token")
                if not token:
                    logger.warning("Token missing in request to files endpoint.")
                    return self.unauthorized()

                try:
                    payload = jwt.decode(
                        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                    )
                    file_path = payload.get("file_path")
                    if not file_path or not path.endswith(file_path):
                        logger.warning("Invalid or mismatched file path in token.")
                        return self.unauthorized()
                except JWTError as e:
                    logger.error(f"JWT decoding error for files: {e}")
                    return self.unauthorized()

            elif path in ["/docs", "/redoc", "/openapi.json"]:
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    return self.unauthorized(realm="Access to the API docs")

                try:
                    scheme, credentials = auth_header.split()
                    if scheme.lower() != "basic":
                        return self.unauthorized(realm="Access to the API docs")

                    decoded = base64.b64decode(credentials).decode("ascii")
                    username, password = decoded.split(":")
                    if not (
                        secrets.compare_digest(username, settings.API_LOGIN)
                        and secrets.compare_digest(password, settings.API_PASSWORD)
                    ):
                        return self.unauthorized(realm="Access to the API docs")
                except (ValueError, base64.binascii.Error) as e:
                    logger.error(f"Error parsing authorization header: {e}")
                    return self.unauthorized(realm="Access to the API docs")

            response = await call_next(request)
        except Exception as e:
            logger.error(f"Error in CombinedAuthMiddleware: {e}")
            raise e

        return response


class CombinedDBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        analytical_request_id = str(uuid.uuid4())
        start_time = datetime.now()

        request.state.db = SessionLocal()
        request.state.db.begin()  # Explicitly begin a transaction

        try:
            response = await call_next(request)
            request.state.db.commit()  # Commit transaction after request handling
        except (OperationalError, DBAPIError) as e:
            request.state.db.rollback()  # Rollback on database-related exceptions
            logger.error(f"Database error in middleware: {e}")
            raise e
        except Exception as e:
            request.state.db.rollback()  # Rollback on general exceptions
            logger.error(f"Error in CombinedDBSessionMiddleware: {e}")
            raise e
        finally:
            request.state.db.close()  # Always close the session

            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Request {analytical_request_id} ended for path: {request.url.path}. Duration: {duration:.2f} ms"
            )

        return response
