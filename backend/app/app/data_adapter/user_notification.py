from app.database import Base
from sqlalchemy import Column, ForeignKey, Integer


class UserNotification(Base):
    __tablename__ = "user_notification"
    user_notification_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    notification_id = Column(
        Integer, ForeignKey("notification.notification_id"), nullable=False
    )
