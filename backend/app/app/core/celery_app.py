# app/core/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.context_manager import get_db_session
from celery.signals import worker_init
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy.orm
from app.core.config import settings


celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
)

# Ensure broker connection retries on startup
celery_app.conf.broker_connection_retry_on_startup = True

# Create a scoped session
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False))


@worker_init.connect(weak=False)
def initialize_session(**kwargs):
    engine = create_engine(settings.DATABASE_URI)
    Session.configure(bind=engine)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        60.0,  # Run every 60 seconds
        update_event_statuses_task.s(),
        name="update event statuses every minute",
    )


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
    # sender.add_periodic_task(
    #     crontab(hour=0, minute=0),  # Run daily at midnight
    #     update_event_statuses_task.s(),
    #     name="update event statuses daily",
    # )
    print("DEBUG: Periodic tasks set up.")
    sender.add_periodic_task(
        60.0,  # Run every 60 seconds
        update_event_statuses_task.s(),
        name="update event statuses every minute",
    )

    # Run at midnight (00:00) every day
    sender.add_periodic_task(
        crontab(hour=0, minute=0),  # This sets it to run at 00:00
        check_upcoming_reservations_task.s(),
        name="check upcoming reservations daily at midnight"
    )


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


@celery_app.task
async def check_upcoming_reservations_task():
    """Check for upcoming reservations and send notifications and emails."""
    from datetime import datetime, timedelta
    from app.data_adapter.reservation import Reservation, ReservationStatus
    from app.data_adapter.notification import Notification, NotificationType
    from app.data_adapter.user import User
    from app.data_adapter.email_log import EmailLog, EmailLogTemplates, EmailLogTypes, EmailLogLanguage, EmailLogStatus
    from app.service.email_service import EmailService
    import json

    session = Session()
    try:
        today = datetime.utcnow().date()
        three_days_later = today + timedelta(days=3)
        
        print(f"DEBUG: Checking reservations for date: {three_days_later}")
        
        from app.data_adapter.event import EventDate
        from app.service.email_service import EmailService
        # Query reservations for three days from now
        reservations = session.query(Reservation).join(
            Reservation.event_date
        ).filter(
            Reservation.status != ReservationStatus.CANCELLED,
            EventDate.date == three_days_later
        ).all()

        notification_count = 0
        email_count = 0
        
        for reservation in reservations:
            try:
                user = User.get_user_by_id(reservation.user_id)
                if not user:
                    continue

                # Create notification
                notification_text = (
                    f"Pripomienka: Vaša rezervácia na podujatie '{reservation.event.title}' "
                    f"je naplánovaná na {reservation.event_date.date.strftime('%d.%m.%Y')}. "
                    f"Kód rezervácie: {reservation.local_reservation_code}"
                )
                
                Notification.create_notification(
                    notification_text,
                    today,
                    NotificationType.INFO,
                    [reservation.user_id]
                )
                notification_count += 1

                # Prepare email data
                email_data = {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "event_title": reservation.event.title,
                    "event_date": reservation.event_date.date.strftime('%d.%m.%Y'),
                    "event_time": reservation.event_date.time.strftime('%H:%M'),
                    "event_location": f"{reservation.event.city}, {reservation.event.address}",
                    "reservation_code": reservation.local_reservation_code,
                    "number_of_students": reservation.number_of_students,
                    "number_of_teachers": reservation.number_of_teachers
                }

                # Create email log
                email_log = EmailLog.create_new_email_log(
                    user_id=user.user_id,
                    recipient_email=user.user_email,
                    subject=f"Pripomienka rezervácie - {reservation.event.title}",
                    email_data=json.dumps(email_data),
                    email_template=EmailLogTemplates.SCHOOL_REPRESENTATIVE_DATE_INCOMING,
                    email_type=EmailLogTypes.SCHOOL_REPRESENTATIVE_DATE_INCOMING,
                    language=EmailLogLanguage.SK,
                    status=EmailLogStatus.PENDING
                )

                # Send email
                await EmailService.send_new_email(email_log)
                email_count += 1
                
                print(f"DEBUG: Created notification and sent email for reservation {reservation.id}")
                
            except Exception as e:
                print(f"Error processing reservation {reservation.id}: {str(e)}")
                continue

        print(f"Created {notification_count} notifications and sent {email_count} emails for upcoming reservations")
        session.commit()
        
    except Exception as e:
        print(f"Error in check_upcoming_reservations_task: {str(e)}")
        session.rollback()
    finally:
        session.close()

@celery_app.task
def update_event_statuses_task():
    """Update the status of past events."""
    from app.data_adapter.event import EventDate

    session = Session()
    try:
        print("DEBUG: Session created.")
        updated_count = EventDate.update_past_event_statuses(session)
        print(f"Updated {updated_count} event statuses.")
        session.commit()
    except Exception as e:
        print(f"Error in update_event_statuses_task: {str(e)}")
        session.rollback()
    finally:
        session.close()
