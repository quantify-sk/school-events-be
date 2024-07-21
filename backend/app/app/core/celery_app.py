# app/core/celery_app.py
from celery import Celery


celery_app = Celery(
    "tasks",
    broker="redis://redis:6399/0",
    backend="redis://redis:6399/0",
)

# Ensure broker connection retries on startup
celery_app.conf.broker_connection_retry_on_startup = True


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs) -> None:
    """Configure periodic tasks for the Celery app.

    Args:
        sender (Celery): The Celery application instance.
    """
    # sender.add_periodic_task(
    #     30.0, expire_locks_task.s(), name="expire user locks every 30 seconds"
    # )
    # sender.add_periodic_task(
    #     60.0, remove_unused_tags_task.s(), name="remove unused tags every 60 seconds"
    # )
    # sender.add_periodic_task(
    #     crontab(hour=5, minute=0),
    #     remove_unused_files_task.s(),
    #     name="remove unused files every day at 5am",
    # )
    pass


# @celery_app.task
# def expire_locks_task():
#     """Expire all locks that have surpassed their duration."""
#     from app.database import SessionLocal
#     from app.data_adapter.user_lock import UserLock

#     # Create a new database session
#     db = SessionLocal()
#     try:
#         # Call the UserLockService method with the session
#         UserLock.cron_delete_expired_locks(db)
#     finally:
#         # Ensure the session is properly closed
#         db.close()


# @celery_app.task
# def remove_unused_tags_task():
#     """Expire all locks that have surpassed their duration."""
#     from app.database import SessionLocal
#     from app.data_adapter.tag import Tag

#     # Create a new database session
#     db = SessionLocal()
#     try:
#         # Call the UserLockService method with the session
#         Tag.cron_delete_unused_tags(db)
#     finally:
#         # Ensure the session is properly closed
#         db.close()


# @celery_app.task
# def remove_unused_files_task():
#     """Expire all locks that have surpassed their duration."""
#     from app.database import SessionLocal
#     from app.data_adapter.file import File

#     # Create a new database session
#     db = SessionLocal()
#     try:
#         # Call the UserLockService method with the session
#         File.cron_delete_unused_files(db)
#     finally:
#         # Ensure the session is properly closed
#         db.close()
