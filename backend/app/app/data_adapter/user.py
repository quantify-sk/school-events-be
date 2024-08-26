import app.api.v1.endpoints
import app.logger
from datetime import datetime, timedelta
import starlette.responses
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pytz import timezone
from app.database import Base
from app.models.get_params import ParameterValidator
from app.models.user import (
    UserCreateModel,
    UserModel,
    UserStatus,
    UserTokenData,
    UserUpdateModel,
    UserRole,
)
from pydantic import EmailStr
from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, ForeignKey, or_
from sqlalchemy.orm import Mapped, relationship
from app.data_adapter.reservation import Reservation
from app.data_adapter.school import School
import app.context_manager
from app.context_manager import get_db_session
from app.data_adapter.report import Report, ReportType
if TYPE_CHECKING:
    from app.data_adapter.notification import Notification
    

from app.logger import logger
from app.models.user import UserModel
from app.models.school import SchoolUpdateModel
from sqlalchemy.orm import joinedload


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

    # Locked login attempts
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    account_locked_until = Column(DateTime, nullable=True)
    organized_events = relationship("Event", back_populates="organizer")

    school_id = Column(Integer, ForeignKey("school.id"))
    school = relationship("School", back_populates="representatives")

    # New field for employee accounts
    parent_organizer_id = Column(Integer, ForeignKey("user.user_id"), nullable=True)
    employees = relationship("User", backref="parent_organizer", remote_side=[user_id])
    reservations = relationship("Reservation", back_populates="user")
    waiting_list = relationship("WaitingList", back_populates="user")
    reports = relationship("Report", back_populates="user")

    def build_user_token_data(self) -> UserTokenData:
        return UserTokenData(
            user_id=self.user_id,
        )

    def is_account_locked(self) -> tuple[bool, Optional[datetime]]:
        """
        Check if the user account is locked.

        Returns:
            tuple[bool, Optional[datetime]]: A tuple containing a boolean indicating if the account is locked,
            and the datetime when the account will be unlocked (if it is locked).
        """
        print("self.account_locked_until", self.account_locked_until)
        if self.account_locked_until and self.account_locked_until > datetime.now():
            return True, self.account_locked_until
        return False, None

    def __init__(
        self,
        first_name: str,
        last_name: str,
        user_email: str,
        password_hash: str,
        role: UserRole,
        school_id: Optional[int] = None,
        parent_organizer_id: Optional[int] = None,
        **kwargs,
    ):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        self.password_hash = password_hash
        self.role = role
        self.school_id = school_id
        self.parent_organizer_id = parent_organizer_id
        for key, value in kwargs.items():
            setattr(self, key, value)

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
            school=self.school._to_model() if self.school else None,
            parent_organizer_id=self.parent_organizer_id,
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
        print("user", user._to_model())
        return user._to_model() if user else None

    @classmethod
    def create_new_user(cls, user_data: UserCreateModel) -> UserModel:
        """
        Create a new user. The school association and error handling are managed in the service layer.

        Args:
            user_data (UserCreateModel): The data of the new user.

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
            email_verified=user_data.email_verified
            if user_data.email_verified
            else False,
            preferred_language=user_data.preferred_language,
            profile_picture=user_data.profile_picture,
            subscription=user_data.subscription,
            status= UserStatus.ACTIVE if user_data.role == UserRole.ORGANIZER else UserStatus.INACTIVE,
            school_id=user_data.school_id,  # This is set in the service layer if applicable
            parent_organizer_id=user_data.parent_organizer_id,  # New field for employee accounts
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
        Delete a user by ID from the database.

        This method will permanently remove the user from the database. It will also
        delete any related data that has a foreign key relationship with CASCADE delete.

        Args:
            user_id (int): The ID of the user to delete.

        Returns:
            bool: True if the user was deleted successfully, False if the user was not found.

        Raises:
            SQLAlchemyError: If there's an error during the database operation.
        """
        from app.context_manager import get_db_session

        try:
            with get_db_session() as db:
                user = db.query(cls).filter(cls.user_id == user_id).first()
                if user:
                    db.delete(user)
                    db.commit()
                    logger.info(f"User with ID {user_id} has been deleted successfully.")
                    return True
                else:
                    logger.warning(f"Attempted to delete non-existent user with ID {user_id}.")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user with ID {user_id}: {str(e)}")
            raise

    @classmethod
    def update_user_by_id(cls, user_id: int, user_data: UserUpdateModel) -> Optional[UserModel]:
        """
        Update a user by ID, including school data for school representatives.

        This method updates the user's information and, if the user is a school representative,
        also updates the associated school information.

        Args:
            user_id (int): The ID of the user to update.
            user_data (UserUpdateModel): The data of the user to update, including school data.

        Returns:
            Optional[UserModel]: The updated user model if found and updated successfully, otherwise None.

        Raises:
            SQLAlchemyError: If there's an error during the database operation.
        """
        from app.context_manager import get_db_session

        try:
            with get_db_session() as db:
                user = db.query(cls).options(joinedload(cls.school)).filter(cls.user_id == user_id).first()
                if not user:
                    logger.warning(f"Attempted to update non-existent user with ID {user_id}.")
                    return None

                # Update user fields
                for field, value in user_data.dict(exclude_unset=True).items():
                    if field != 'school' and hasattr(user, field):
                        setattr(user, field, value)

                # Update school data if user is a school representative
                if user.role == UserRole.SCHOOL_REPRESENTATIVE and user_data.school:
                    if not user.school:
                        user.school = School()
                    
                    school_data: SchoolUpdateModel = user_data.school
                    for field, value in school_data.dict(exclude_unset=True).items():
                        setattr(user.school, field, value)

                db.commit()
                db.refresh(user)
                logger.info(f"User with ID {user_id} has been updated successfully.")
                return user._to_model()

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating user with ID {user_id}: {str(e)}")
            raise

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

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=5)

    @classmethod
    def handle_failed_login(cls, user_id: int) -> None:
        """
        Handle a failed login attempt.

        Args:
            user_id (int): The ID of the user who failed to log in.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()
        if user:
            user.failed_login_attempts += 1
            slovakia_tz = timezone("Europe/Bratislava")
            current_time = datetime.now(slovakia_tz)
            user.last_failed_login = current_time

            if user.failed_login_attempts >= cls.MAX_LOGIN_ATTEMPTS:
                user.account_locked_until = current_time + cls.LOCKOUT_DURATION

            db.commit()

    @classmethod
    def reset_failed_login_attempts(cls, user_id: int) -> None:
        """
        Reset failed login attempts for a user.

        Args:
            user_id (int): The ID of the user to reset failed login attempts for.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()
        if user:
            user.failed_login_attempts = 0
            user.last_failed_login = None
            user.account_locked_until = None
            db.commit()

    @classmethod
    def get_user_role(cls, user_id: int) -> Optional[str]:
        """
        Get the role of a user by their ID.

        This class method queries the database to find a user by their ID
        and returns their role if found.

        Args:
            user_id (int): The ID of the user whose role we want to retrieve.

        Returns:
            Optional[str]: The user's role if found, None otherwise.
        """
        from app.context_manager import get_db_session

        db = get_db_session()
        user = db.query(cls).filter(cls.user_id == user_id).first()

        if user:
            return user.role
        return None

    @classmethod
    def get_user_role(cls, user_id: int) -> Optional[str]:
        """
        Get the role of a user by their ID.

        Args:
            user_id (int): The ID of the user whose role we want to retrieve.

        Returns:
            Optional[str]: The user's role if found, None otherwise.
        """
        with get_db_session() as db:
            user = db.query(cls).filter(cls.user_id == user_id).first()
            return user.role if user else None

    @classmethod
    def get_users_by_status(
        cls,
        user_status: UserStatus,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[List[Dict[str, str]]] = None,
        sorting_params: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[List[UserModel], int]:
        """
        Get users by status with pagination, filtering, and sorting.

        Args:
            user_status (UserStatus): The status of users to retrieve.
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[List[Dict[str, str]]]): The filters to apply.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters to apply.

        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing a list of user dictionaries and the total count.
        """
        with get_db_session() as session:
            query = session.query(cls).filter(cls.status == user_status)

            # Apply filters and sorting
            query = ParameterValidator.apply_filters_and_sorting(
                query, cls, filter_params, sorting_params
            )

            # Get total count
            total_count = query.count()

            # Apply pagination
            users = (
                query.offset((current_page - 1) * items_per_page)
                .limit(items_per_page)
                .all()
            )

            return [user._to_model() for user in users], total_count

    

    @classmethod
    def update_user_status(cls, user_id: int, new_status: UserStatus, reason: Optional[str] = None) -> Optional[UserModel]:
        """
        Update a user's status and optionally store the reason for the status change.

        Args:
            user_id (int): The ID of the user to update.
            new_status (UserStatus): The new status to set for the user.
            reason (Optional[str]): The reason for the status change, if applicable.

        Returns:
            Optional[UserModel]: The updated UserModel object if found, None otherwise.
        """
        with get_db_session() as session:
            user = session.query(cls).filter(cls.user_id == user_id).first()
            if user:
                user.status = new_status
                session.commit()
                return user._to_model()
            return None

    @classmethod
    def get_employees(cls, organizer_id: int) -> List[UserModel]:
        """
        Get all employees for a given organizer.

        Args:
            organizer_id (int): The ID of the organizer.

        Returns:
            List[UserModel]: A list of employee user models.
        """
        with get_db_session() as session:
            employees = (
                session.query(cls).filter(cls.parent_organizer_id == organizer_id).all()
            )
            return [employee._to_model() for employee in employees]

    @classmethod
    def add_employee(
        cls, organizer_id: int, employee_data: UserCreateModel
    ) -> UserModel:
        """
        Add a new employee for an organizer.

        Args:
            organizer_id (int): The ID of the organizer.
            employee_data (UserCreateModel): The data for the new employee.

        Returns:
            UserModel: The created employee user model.
        """
        employee_data.parent_organizer_id = organizer_id
        employee_data.role = UserRole.EMPLOYEE
        return cls.create_new_user(employee_data)

    @classmethod
    def remove_employee(cls, employee_id: int) -> bool:
        """
        Remove an employee (set their status to DELETED).

        Args:
            employee_id (int): The ID of the employee to remove.

        Returns:
            bool: True if the employee was successfully removed, False otherwise.
        """
        return cls.delete_user_by_id(employee_id)

    @classmethod
    def get_organizer_with_employees(
        cls, organizer_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get an organizer's details along with their employees.

        Args:
            organizer_id (int): The ID of the organizer.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the organizer's details and a list of their employees,
                                      or None if the organizer is not found.
        """
        with get_db_session() as session:
            organizer = (
                session.query(cls)
                .filter(cls.user_id == organizer_id, cls.role == UserRole.ORGANIZER)
                .first()
            )
            if organizer:
                organizer_data = organizer._to_model().dict()
                organizer_data["employees"] = [
                    employee._to_model().dict() for employee in organizer.employees
                ]
                return organizer_data
            return None
        
    @classmethod
    def search_organizers(
        cls,
        current_page: int,
        items_per_page: int,
        filter_params: Optional[Dict[str, Any]] = None,
        sorting_params: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[List[UserModel], int]:
        """
        Search organizers with pagination, filtering, and sorting.
    
        Args:
            current_page (int): The current page number.
            items_per_page (int): The number of items per page.
            filter_params (Optional[Dict[str, Any]]): The filters to apply.
            sorting_params (Optional[List[Dict[str, str]]]): The sorting parameters to apply.
    
        Returns:
            Tuple[List[Dict[str, Any]], int]: A tuple containing a list of organizer dictionaries and the total count.
        """
        with get_db_session() as session:
            query = session.query(cls).filter(cls.role == UserRole.ORGANIZER)
    
            # Apply filters and sorting using ParameterValidator
            query = ParameterValidator.apply_filters_and_sorting(
                query,
                cls,
                filter_params,
                None
            )
    
            # Get total count
            total_count = query.count()
    
            # Apply pagination
            organizers = (
                query.offset((current_page - 1) * items_per_page)
                .limit(items_per_page)
                .all()
            )
    
            return [organizer._to_model() for organizer in organizers], total_count