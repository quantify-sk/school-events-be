import uuid
from contextvars import ContextVar
from typing import Generator, Optional

from app.dependencies import get_db
from app.logger import logger
from app.models.user import UserModel, UserStatus, UserTokenData
from app.utils.exceptions import CustomAuthException
from fastapi import Depends, Request
from sqlalchemy.orm import Session

# Context variables
context_db_session: ContextVar[Session] = ContextVar("db_session", default=None)
context_id_api: ContextVar[str] = ContextVar("id_api", default=None)
context_log_meta: ContextVar[dict] = ContextVar("log_meta", default={})
context_id_user: ContextVar[Optional[str]] = ContextVar("id_user", default=None)
context_actor_user_data: ContextVar[Optional[UserTokenData]] = ContextVar(
    "actor_user_data", default=None
)
context_set_db_session_rollback: ContextVar[bool] = ContextVar(
    "set_db_session_rollback", default=False
)


async def build_request_context(
    request: Request,
    db: Session = Depends(get_db),
) -> Generator[None, None, None]:
    """
    Context manager to build request context by setting up various dependencies and performing authentication checks.

    Args:
        request (Request): The incoming request object.
        db (Session): The database session. Defaults to Depends(get_db).

    Raises:
        CustomAuthException: If there is an authentication error.

    Yields:
        None: The context manager for the request.
    """
    from app.data_adapter.notification import Notification
    from app.data_adapter.user import User

    context_db_session.set(db)
    context_id_api.set(str(uuid.uuid4()))
    context_id_user.set(request.headers.get("X-User-ID"))

    # User part
    user_data_from_context: UserTokenData = context_actor_user_data.get()
    if user_data_from_context:
        try:
            user: Optional[UserModel] = User.get_user_by_id(
                user_data_from_context.user_id
            )
            if not user or user.status != UserStatus.ACTIVE:
                raise CustomAuthException()

            unread_notification = Notification.exists_unread_notifications(
                user_data_from_context.user_id
            )
            log_meta = context_log_meta.get()
            log_meta["unread_notification"] = unread_notification
            context_log_meta.set(log_meta)

        except CustomAuthException as e:
            logger.info(
                f"Authentication error for user: {user_data_from_context.user_id} - {e}"
            )
            raise
        except Exception:
            logger.error(
                "Unexpected error in user validation",
                exc_info=True,
                extra=context_log_meta.get(),
            )
            raise CustomAuthException()

    log_meta = {
        "id_api": context_id_api.get(),
        "request_id": request.headers.get("X-Request-ID"),
        "id_user": context_id_user.get(),
        "actor_user": context_actor_user_data.get(),
        "unread_notification": context_log_meta.get().get("unread_notification", False),
    }
    context_log_meta.set(log_meta)
    logger.info("REQUEST_INITIATED", extra=log_meta)


def get_db_session() -> Session:
    """common method to get db session from context variable"""
    return context_db_session.get()
