from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from app.database import Base
from app.models.get_params import ParameterValidator
from app.models.user import (
    UserCreateModel,
    UserModel,
    UserStatus,
    UserUpdateModel,
    UserRole,
)
from pydantic import EmailStr
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.data_adapter.notification import Notification


class User(Base):
    __tablename__ = "user"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150), nullable=False)
    user_email = Column(String(255), index=True, unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    registration_date = Column(DateTime, nullable=False, default=datetime.now)
    email_verified = Column(Boolean, nullable=False, default=False)
    preferred_language = Column(String(50), nullable=True)
    profile_picture = Column(String(255), nullable=True)
    subscription = Column(String(50), nullable=True)
    status = Column(
        Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", secondary="user_notification", back_populates="users"
    )

    def __init__(
        self,
        first_name: str,
        last_name: str,
        user_email: EmailStr,
        password_hash: str,
        role: UserRole = UserRole.USER,
        email_verified: bool = False,
        preferred_language: str = None,
        profile_picture: str = None,
        subscription: str = None,
    ):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        self.password_hash = password_hash
        self.role = role
        self.email_verified = email_verified
        self.preferred_language = preferred_language
        self.profile_picture = profile_picture
        self.subscription = subscription

    def _to_model(self) -> UserModel:
        """
        Convert the User ORM object to a Pydantic model.
        """
        return UserModel(
            user_id=self.user_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            first_name=self.first_name,
            last_name=self.last_name,
            user_email=self.user_email,
            status=self.status,
            role=self.role,
            password_hash=self.password_hash,
            registration_date=self.registration_date,
            email_verified=self.email_verified,
            preferred_language=self.preferred_language,
            profile_picture=self.profile_picture,
            subscription=self.subscription,
        )

    @classmethod
    def get_user_by_email(cls, email: str) -> UserModel | None:
        """
        Get a user by email.

        Args:
            email (str): The email of the user.

        Returns:
            UserModel | None: The user model if found, otherwise None.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_email == email).first()
        return user._to_model() if user else None

    @classmethod
    def get_user_object_by_email(cls, email: str) -> "User":
        """
        Get a user by email.

        Args:
            email (str): The email of the user.

        Returns:
            UserModel | None: The user model if found, otherwise None.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_email == email).first()
        return user

    @classmethod
    def get_user_by_id(cls, user_id: int) -> UserModel | None:
        """
        Get a user by ID.

        Args:
            user_id (int): The ID of the user.

        Returns:
            UserModel | None: The user model if found, otherwise None.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()
        return user._to_model() if user else None

    @classmethod
    def create_new_user(cls, user_data: UserCreateModel) -> UserModel:
        """
        Create a new user.

        Args:
            user_data (UserModel): The data of the new user.

        Returns:
            UserModel: The created user model.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        new_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            user_email=user_data.user_email,
            password_hash=user_data.password_hash,
            role=user_data.role if user_data.role else "user",
            email_verified=(
                user_data.email_verified if user_data.email_verified else False
            ),
            preferred_language=user_data.preferred_language,
            profile_picture=user_data.profile_picture,
            subscription=user_data.subscription,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user._to_model()

    @classmethod
    def get_all_users(cls) -> list[UserModel]:
        """
        Get all users.

        Returns:
            list[UserModel]: A list of user models.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        users = db.query(cls).all()
        return [user._to_model() for user in users]

    @classmethod
    def delete_user_by_id(cls, user_id: int) -> bool:
        """
        Delete a user by ID.

        Args:
            user_id (int): The ID of the user to delete.

        Returns:
            bool: True if the user was deleted successfully, False otherwise.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()
        if user:
            user.status = UserStatus.DELETED
            db.commit()
            db.refresh(user)
            return True

        return False

    @classmethod
    def update_user_by_id(
        cls, user_id: int, user_data: UserUpdateModel
    ) -> UserModel | None:
        """
        Update a user by ID.

        Args:
            user_id (int): The ID of the user to update.
            user_data (UserUpdateModel): The data of the user to update.

        Returns:
            UserModel | None: The updated user model if found, otherwise None.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()
        if user:
            user.first_name = (
                user_data.first_name if user_data.first_name else user.first_name
            )
            user.last_name = (
                user_data.last_name if user_data.last_name else user.last_name
            )
            user.user_email = (
                user_data.user_email if user_data.user_email else user.user_email
            )
            user.status = user_data.status if user_data.status else user.status
            user.role = user_data.role if user_data.role else user.role
            user.email_verified = (
                user_data.email_verified
                if user_data.email_verified
                else user.email_verified
            )
            user.preferred_language = (
                user_data.preferred_language
                if user_data.preferred_language
                else user.preferred_language
            )
            user.profile_picture = (
                user_data.profile_picture
                if user_data.profile_picture
                else user.profile_picture
            )
            user.subscription = (
                user_data.subscription if user_data.subscription else user.subscription
            )

            db.commit()
            db.refresh(user)
            return user._to_model()

        return None

    @classmethod
    def get_users(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[List[Dict[str, str]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> tuple[List[UserModel], int]:
        """
        Get users by filters.

        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[FilterParams]): The filter parameters.
            sorting_params (Optional[Dict[str, str]]): The sorting parameters.

        Returns:
            List[UserModel]: The list of users if found, otherwise an empty list.
            int: Total count of users matching the filter criteria.
        """
        from app.context_manager import get_db_session

        # Get users
        db = get_db_session()
        query = db.query(User)

        query = ParameterValidator.apply_filters_and_sorting(
            query,
            User,
            filter_params,
            sorting_params,
        )

        total_count = query.count()
        users = (
            query.offset((current_page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )

        return [user._to_model() for user in users], total_count
