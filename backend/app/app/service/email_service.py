import json
import os
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm.session import Session

from app.context_manager import context_request
from app.core.config import settings
from app.data_adapter.email_log import EmailLog, EmailLogModel, EmailLogStatus
from app.logger import logger
from app.core.config import settings


def get_url_for(name: str, **path_params):
    """Helper function to get URL from request context."""
    request = context_request.get()
    if request:
        return request.url_for(name, **path_params)
    else:
        raise RuntimeError("Request context is not available.")



# Get the absolute path to the templates directory
TEMPLATE_FOLDER = Path(__file__).parent.parent / "templates"

# Create template directories if they don't exist
def ensure_template_directories():
    directories = [
        TEMPLATE_FOLDER,
        TEMPLATE_FOLDER / "sk",
        TEMPLATE_FOLDER / "en"
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Template directory ensured: {directory}")

# Create template directories
ensure_template_directories()

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)

# Jinja2 environment setup
env = Environment(loader=FileSystemLoader(conf.TEMPLATE_FOLDER))
env.globals["url_for"] = get_url_for


class EmailService:
    """
    Service class for handling email operations.
    """

    @staticmethod
    async def send_batch_email(db: Session) -> None:
        """
        Send batch emails, limiting to 50 emails at a time.

        Args:
            db (Session): SQLAlchemy database session.

        Returns:
            None
        """

        logger.info("Sending batch emails...")
        if settings.SENDING_NOTIFICATIONS:
            pending_emails = EmailLog.get_pending_email_logs(db, limit=50)

            if not pending_emails:
                logger.info("No pending emails found.")
                return

            for email in pending_emails:
                try:
                    await EmailService._send_email(db, email)
                    EmailLog.update_email_log_status_with_db(
                        db,
                        email.email_log_id,
                        EmailLogStatus.SUCCESS,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email {email.email_log_id}: {e}")
                    EmailService._handle_email_error(email.email_log_id, e)

    @staticmethod
    async def _send_email(db, pending_email: EmailLogModel):
        """
        Helper function to send an individual email.
        """
        stored_data = json.loads(pending_email.email_data)
        recipients = [pending_email.recipient_email]

        template_name = f"{pending_email.language.value}/{pending_email.email_template.value}".lower()
        template = env.get_template(template_name)
        html_content = template.render(stored_data)

        message = MessageSchema(
            subject=pending_email.subject,
            recipients=recipients,
            body=html_content,
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        await fm.send_message(message)

    @staticmethod
    def _handle_email_error(db: Session, email_log_id: int, error: Exception):
        """
        Handle errors during email sending.
        """
        logger.error(f"Email sending failed for {email_log_id}: {error}")
        EmailLog.update_email_log_status_with_db(
            db, email_log_id, EmailLogStatus.FAILED
        )
        EmailLog.update_email_log_response_with_db(db, email_log_id, str(error))

    @staticmethod
    async def send_new_email(
        pending_email: EmailLogModel,
        attachment_file_paths: list[str] | None = None,
    ):
        """
        Send a new email, with an optional attachment.

        Args:
            pending_email (EmailLogModel): The email log model containing the email details.
            attachment_data (Optional[bytes]): Attachment content, defaults to None.
            attachment_filename (Optional[str]): Filename for the attachment, defaults to None.
        """
        try:
            print("Sending email...")
            print(pending_email)
            stored_data = json.loads(pending_email.email_data)
            recipients = (
                [pending_email.recipient_email] if pending_email.recipient_email else []
            )
            attachments = []

            # Prepare attachment if provided
            if attachment_file_paths:  # Check if list exists
                for attachment_file_path in attachment_file_paths:
                    logger.info(f"Checking attachment path: {attachment_file_path}")  # Log actual path
                    if not isinstance(attachment_file_path, (str, bytes, os.PathLike)):  # Check actual path
                        logger.error(f"Invalid attachment path: {attachment_file_path}")
                        continue
                    
                    if os.path.exists(attachment_file_path):  # Check if file exists
                        logger.info(f"File exists and is readable: {attachment_file_path}")
                        attachments.append(attachment_file_path)
                    else:
                        logger.error(f"File does not exist: {attachment_file_path}")
                        
            print(settings.SENDING_NOTIFICATIONS)
            if settings.SENDING_NOTIFICATIONS:
                print("I am in the Settings.sending")
                
                template_name = f"{pending_email.language.value}/{pending_email.email_template.value}".lower()
                logger.info(f"Loading template: {TEMPLATE_FOLDER / template_name}")
                # Load the template
                template = env.get_template(template_name)
                # Render the template with context
                html_content = template.render(stored_data)

                message = MessageSchema(
                    subject=pending_email.subject,
                    recipients=recipients,
                    body=html_content,
                    subtype=MessageType.html,
                    attachments=attachments,
                )

                print("Sending email message...")
                print(message)

                # Send the message using the formatted template_name
                fm = FastMail(conf)
                await fm.send_message(message)

            logger.info(f"Email sent successfully: {pending_email.email_log_id}")
            EmailLog.update_email_log_status(
                pending_email.email_log_id, EmailLogStatus.SUCCESS
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            EmailLog.update_email_log_status(
                pending_email.email_log_id, EmailLogStatus.FAILED
            )
            EmailLog.update_email_log_response(pending_email.email_log_id, str(e))
        finally:
            # Pokus o smazání souborů vždy, bez ohledu na výsledek odesílání
            logger.info(f"Deleting attachments: {attachments}")