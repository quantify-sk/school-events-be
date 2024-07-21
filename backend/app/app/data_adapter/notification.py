from datetime import date
from typing import TYPE_CHECKING, List, Optional

from app.database import Base
from app.models.notification import (
    NotificationCreateModel,
    NotificationModel,
    NotificationStatus,
    NotificationType,
)
from sqlalchemy import Boolean, Column, Date, Enum, Integer, String
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.data_adapter.user import User


class Notification(Base):
    __tablename__ = "notification"
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    notification_content = Column(String(255), nullable=False)

    notification_date = Column(Date, nullable=False)
    notification_type = Column(
        Enum(NotificationType),
        nullable=False,
        default=NotificationType.INFO,
        index=True,
    )
    notification_status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.UNREAD,
        index=True,
    )
    send_notification = Column(Boolean, nullable=False, default=False)
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_notification", back_populates="notifications"
    )

    def __init__(
        self,
        notification_content: str,
        notification_date: date,
        notification_type: NotificationType,
        notification_status: NotificationStatus = NotificationStatus.UNREAD,
    ):
        self.notification_content = notification_content
        self.notification_date = notification_date
        self.notification_type = notification_type
        self.notification_status = notification_status

    def _to_model(self):
        return NotificationModel(
            notification_id=self.notification_id,
            notification_content=self.notification_content,
            notification_date=self.notification_date,
            notification_type=self.notification_type,
            notification_status=self.notification_status,
            send_notification=self.send_notification,
        )

    @classmethod
    def create_notification(
        cls,
        notification_content: str,
        notification_date: date,
        notification_type: NotificationType,
        users: Optional[List[int]] = None,
    ) -> NotificationModel:
        from app.context_manager import get_db_session
        from app.data_adapter.user import User

        db = get_db_session()
        new_notification = Notification(
            notification_content=notification_content,
            notification_date=notification_date,
            notification_type=notification_type,
            notification_status=NotificationStatus.UNREAD,
        )
        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        if users:
            # Fetch user instances and add them to the notification
            for user_id in users:
                user = db.query(User).filter(User.user_id == user_id).first()
                if user:
                    new_notification.users.append(user)
            db.commit()  # Commit once after all users are added

        return new_notification._to_model()

    @classmethod
    def get_notification_by_id(
        cls, notification_id: int
    ) -> Optional[NotificationModel]:
        from app.context_manager import get_db_session

        db = get_db_session()
        notification = (
            db.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )
        if notification:
            return notification._to_model()
        return None

    @classmethod
    def update_notification(
        cls, notification_id: int, notification_data: NotificationCreateModel
    ) -> Optional[NotificationModel]:
        from app.context_manager import get_db_session

        db = get_db_session()
        notification = (
            db.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )
        if notification:
            notification.notification_content = notification_data.notification_content
            notification.notification_date = notification_data.notification_date
            notification.notification_type = notification_data.notification_type
            db.commit()
            db.refresh(notification)
            return notification._to_model()
        return None

    @classmethod
    def delete_notification(cls, notification_id: int) -> bool:
        from app.context_manager import get_db_session

        db = get_db_session()
        notification = (
            db.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )
        if notification:
            notification.notification_status = NotificationStatus.DELETED
            db.commit()
            db.refresh(notification)
            return True

        return False

    @classmethod
    def change_notification_status_to_read(
        cls, notification_id: int
    ) -> Optional[NotificationModel]:
        from app.context_manager import get_db_session

        db = get_db_session()
        notification = (
            db.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )
        if notification:
            notification.notification_status = NotificationStatus.READ
            db.commit()
            db.refresh(notification)
            return notification._to_model()

        return None

    @classmethod
    def get_notifications(
        cls,
        user_id: int,
    ) -> List[NotificationModel]:
        from app.context_manager import get_db_session
        from app.data_adapter.user_notification import UserNotification

        # Get instruments
        db = get_db_session()
        query = (
            db.query(Notification)
            .join(
                UserNotification,
                Notification.notification_id == UserNotification.notification_id,
            )
            .filter(
                UserNotification.user_id == user_id,
                Notification.notification_status != NotificationStatus.DELETED,
            )
            .order_by(
                Notification.notification_date.desc(),
                Notification.notification_id.desc(),
            )
        )

        instruments = query.all()

        return [instrument._to_model() for instrument in instruments]

    @classmethod
    def exists_unread_notifications(cls, user_id: int) -> bool:
        from app.context_manager import get_db_session
        from app.data_adapter.notification import Notification
        from app.data_adapter.user_notification import UserNotification
        from app.models.notification import NotificationStatus

        print("Checking for unread notifications for user_id:", user_id)
        db = get_db_session()

        # Query to check if there exists any unread notifications for the user
        unread_notifications = (
            db.query(Notification)
            .join(UserNotification)
            .filter(
                UserNotification.user_id == user_id,
                Notification.notification_id == UserNotification.notification_id,
                Notification.notification_status == NotificationStatus.UNREAD,
                Notification.send_notification is False,
            )
            .all()
        )

        print("Fetched notifications:", unread_notifications)

        # Update send_notification to True for all fetched unread notifications
        for notification in unread_notifications:
            notification.send_notification = True

        db.commit()

        print("Updated send_notification to True for all fetched notifications")

        # Return True if there are any unread notifications, False otherwise
        return bool(unread_notifications)
