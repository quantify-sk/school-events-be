from app.api.v1.api import api_router as api_router_v1
from app.context_manager import context_id_api, context_set_db_session_rollback
from app.core.config import settings
from app.database import Base, engine
from app.event_listeners import register_event_listeners
from app.logger import logger
from app.models.response import GenericResponseModel, build_api_response
from app.utils.exceptions import (
    CustomAuthException,
    CustomBadRequestException,
    CustomInternalServerErrorException,
    CustomValidationException,
)
from app.utils.middleware import (
    CombinedDBSessionRequestLogMiddleware,
    CombinedAuthMiddleware,
)
from app.utils.response_messages import ResponseMessages
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

# Debug database setup
print("DEBUG: Drop all tables: ")
# Base.metadata.drop_all(bind=engine)
print("DEBUG: Create all tables: ")
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Add the combined middlewares
app.add_middleware(CombinedDBSessionRequestLogMiddleware)
# app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CombinedAuthMiddleware)
app.add_middleware(TrustedHostMiddleware)

# Add CORS middleware if needed
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Serve static files
app.mount("/files", StaticFiles(directory="/files"), name="files")

# Include API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)


# Documentation routes
@app.get("/api/docs", tags=["documentation"], include_in_schema=False)
async def get_swagger_documentation() -> HTMLResponse:
    """Retrieve the Swagger documentation."""
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="docs")


@app.get("/api/openapi.json", tags=["documentation"], include_in_schema=False)
async def openapi() -> dict:
    """Generate the OpenAPI JSON."""
    return get_openapi(title="FastAPI", version="1.0", routes=app.routes)


@app.get("/api/redoc", tags=["documentation"], include_in_schema=False)
async def get_redoc() -> HTMLResponse:
    """Return the ReDoc documentation."""
    return get_redoc_html(openapi_url="/api/openapi.json", title="docs")


# Catch-all route
@app.get("/{path:path}", tags=["Exception"])
def catch_all(path: str):
    """Catch all undefined routes and raise a 404 error."""
    logger.info(f"Route not found: /{path}")
    raise CustomBadRequestException(
        detail=f"{ResponseMessages.ERR_ROUTE_NOT_FOUND}: /{path}"
    )


# Custom exception handler
async def handle_exception(request: Request, exc: HTTPException) -> Response:
    context_set_db_session_rollback.set(True)
    logger.info(f"Application exception occurred: {str(exc)}")

    response = GenericResponseModel(
        api_id=context_id_api.get(),
        error=exc.detail,
        message=exc.detail,
        status_code=exc.status_code,
    )
    return build_api_response(response)


# Register custom exception handlers
exception_handlers = [
    CustomAuthException,
    CustomInternalServerErrorException,
    CustomBadRequestException,
]

# Register custom exception handlers
for exc in exception_handlers:
    app.exception_handler(exc)(handle_exception)


# Handle HTTP exceptions
@app.exception_handler(HTTPException)
async def handle_known_exceptions(request: Request, exc: HTTPException) -> Response:
    return await handle_exception(request, exc)


# Handle request validation exceptions
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    logger.info(f"Validation exception occurred: {str(exc.errors())}")
    custom_exception = CustomValidationException(errors=exc.errors())
    return await handle_exception(request, custom_exception)


# Ensure event listeners are registered only once
register_event_listeners()
