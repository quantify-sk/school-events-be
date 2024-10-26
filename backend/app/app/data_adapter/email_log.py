from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TEXT, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm.session import Session

from app.database import Base
from app.models.email_log import (
    EmailLogLanguage,
    EmailLogModel,
    EmailLogStatus,
    EmailLogTemplates,
    EmailLogTypes,
)

if TYPE_CHECKING:
    from app.data_adapter.user import User


class EmailLog(Base):
    __tablename__ = "email_log"
    email_log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    recipient_email = Column(String(320), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    email_data = Column(TEXT, nullable=False)
    email_template = Column(Enum(EmailLogTemplates), nullable=False)
    status = Column(
        Enum(EmailLogStatus),
        nullable=False,
        default=EmailLogStatus.PENDING,
    )
    language = Column(
        Enum(EmailLogLanguage),
        nullable=False,
        default=EmailLogLanguage.SK,
        index=True,
    )
    email_type = Column(Enum(EmailLogTypes), nullable=False, index=True)
    retry_count = Column(Integer, nullable=False, default=0, index=True)
    response = Column(TEXT, nullable=True)
    priority = Column(Integer, nullable=False, default=100, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )

    # Relationship with User table
    user: Mapped["User"] = relationship("User")

    def __init__(
        self,
        user_id: int,
        recipient_email: str,
        subject: str,
        email_data: str,
        email_template: EmailLogTemplates,
        email_type: EmailLogTypes,
        priority: int = 100,
        status: EmailLogStatus = EmailLogStatus.PENDING,
        language: EmailLogLanguage = EmailLogLanguage.SK,
        retry_count: int = 0,
    ):
        self.user_id = user_id
        self.recipient_email = recipient_email
        self.subject = subject
        self.email_data = email_data
        self.email_template = email_template
        self.email_type = email_type
        self.priority = priority
        self.status = status
        self.language = language
        self.retry_count = retry_count
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def _to_model(self):
        return EmailLogModel(
            email_log_id=self.email_log_id,
            user_id=self.user_id,
            recipient_email=self.recipient_email,
            subject=self.subject,
            email_data=self.email_data,
            email_template=self.email_template,
            status=self.status,
            language=self.language,
            email_type=self.email_type,
            retry_count=self.retry_count,
            response=self.response,
            priority=self.priority,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def create_new_email_log(
        cls,
        user_id: int,
        recipient_email: str,
        subject: str,
        email_data: str,
        email_template: EmailLogTemplates,
        email_type: EmailLogTypes,
        priority: int = 100,
        status: EmailLogStatus = EmailLogStatus.PENDING,
        language: EmailLogLanguage = EmailLogLanguage.SK,
        retry_count: int = 0,
    ) -> Optional[EmailLogModel]:
        from app.context_manager import get_db_session

        db = get_db_session()

        new_email_log = EmailLog(
            user_id=user_id,
            recipient_email=recipient_email,
            subject=subject,
            email_data=email_data,
            email_template=email_template,
            email_type=email_type,
            priority=priority,
            status=status,
            language=language,
            retry_count=retry_count,
        )
        db.add(new_email_log)
        db.commit()
        db.refresh(new_email_log)

        if new_email_log:
            return new_email_log._to_model()

        return None

    @classmethod
    def get_all_pending_email_logs(cls) -> list[EmailLogModel]:
        """Retrieve all email logs with a pending status."""
        from app.context_manager import get_db_session

        db = get_db_session()
        email_logs = (
            db.query(cls)
            .filter(
                EmailLog.status == EmailLogStatus.PENDING,
                EmailLog.retry_count == 0,
            )
            .order_by(EmailLog.priority.asc(), EmailLog.created_at.asc())
            .all()
        )

        return [email_log._to_model() for email_log in email_logs]

    @classmethod
    def update_email_log_status(cls, email_log_id: int, status: EmailLogStatus) -> bool:
        from app.context_manager import get_db_session

        db = get_db_session()
        email_log = db.query(cls).filter(EmailLog.email_log_id == email_log_id).first()

        if email_log:
            email_log.status = status
            if status == EmailLogStatus.FAILED:
                email_log.retry_count += 1

            db.commit()
            return True

        return False

    @classmethod
    def update_email_log_response(cls, email_log_id: int, response: str) -> bool:
        from app.context_manager import get_db_session

        db = get_db_session()
        email_log = db.query(cls).filter(EmailLog.email_log_id == email_log_id).first()

        if email_log:
            email_log.response = response
            db.commit()
            return True

        return False

    @classmethod
    def get_first_pending_email(cls) -> Optional[EmailLogModel]:
        from app.context_manager import get_db_session

        db = get_db_session()
        email_log = (
            db.query(cls)
            .filter(
                EmailLog.status == EmailLogStatus.PENDING,
                EmailLog.retry_count == 0,
            )
            .order_by(EmailLog.priority.asc(), EmailLog.created_at.asc())
            .first()
        )

        if email_log:
            return email_log._to_model()

        return None

    @classmethod
    def get_pending_email_logs(
        cls,
        db: Session,
        limit: int = 50,
    ) -> list[EmailLogModel]:
        email_logs = (
            db.query(EmailLog)
            .filter(
                EmailLog.status == EmailLogStatus.PENDING,
                EmailLog.retry_count == 0,
            )
            .order_by(EmailLog.priority.asc(), EmailLog.created_at.asc())
            .limit(limit)
            .all()
        )

        return [email_log._to_model() for email_log in email_logs]

    @classmethod
    def update_email_log_status_with_db(
        cls,
        db: Session,
        email_log_id: int,
        status: EmailLogStatus,
    ) -> bool:
        email_log = (
            db.query(EmailLog).filter(EmailLog.email_log_id == email_log_id).first()
        )

        if email_log:
            email_log.status = status
            if status == EmailLogStatus.FAILED:
                email_log.retry_count += 1

            db.commit()
            return True

        return False

    @classmethod
    def update_email_log_response_with_db(
        cls,
        db: Session,
        email_log_id: int,
        response: str,
    ) -> bool:
        email_log = (
            db.query(EmailLog).filter(EmailLog.email_log_id == email_log_id).first()
        )

        if email_log:
            email_log.response = response
            db.commit()
            return True

        return False
    
