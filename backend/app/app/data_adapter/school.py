from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from typing import Optional, Dict, Any
from app.context_manager import get_db_session
from app.utils.exceptions import CustomInternalServerErrorException
from app.logger import logger
from app.utils.response_messages import ResponseMessages
from app.models.school import SchoolCreateModel
from app.models.school import SchoolModel


class School(Base):
    """
    SQLAlchemy model representing a school in the system.

    Attributes:
        id (int): The unique identifier for the school.
        name (str): The name of the school.
        ico (str): A unique identification number for the school (IČO).
        address (str): The address of the school.
        district (str): The district (okres) where the school is located.
        region (str): The region (kraj) where the school is located.
        created_at (datetime): Timestamp of when the school record was created.
        updated_at (datetime): Timestamp of the last update to the school record.
        representatives (relationship): Relationship to User model for school representatives.
    """

    __tablename__ = "school"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    ico = Column(String(20), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    district = Column(String(100), nullable=False)
    region = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    number_of_students = Column(Integer, default=0)
    number_of_employees = Column(Integer, default=0)
    psc = Column(String(10), nullable=False)
    city = Column(String(100), nullable=False)

    # Relationship with User (school representatives)
    representatives = relationship("User", back_populates="school")

    def __init__(
        self,
        name: str,
        ico: str,
        address: str,
        district: str,
        region: str,
        number_of_students: int = 0,
        number_of_employees: int = 0,
        psc="00000",
        city="AAAA",
    ):
        """
        Initialize a new School instance.

        Args:
            name (str): The name of the school.
            ico (str): The unique identification number (IČO) for the school.
            address (str): The address of the school.
            district (str): The district (okres) where the school is located.
            region (str): The region (kraj) where the school is located.
        """
        self.name = name
        self.ico = ico
        self.address = address
        self.district = district
        self.region = region
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.number_of_students = number_of_students
        self.number_of_employees = number_of_employees
        self.psc = psc
        self.city = city

    def _to_model(self) -> Dict[str, Any]:
        """
        Convert the School instance to a dictionary representation.

        Returns:
            Dict[str, Any]: A dictionary containing the school's data.
        """
        return {
            "id": self.id,
            "name": self.name,
            "ico": self.ico,
            "address": self.address,
            "district": self.district,
            "region": self.region,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "number_of_students": self.number_of_students,
            "number_of_employees": self.number_of_employees,
            "psc": self.psc,
            "city": self.city,
        }

    @classmethod
    def get_school_by_ico(cls, ico: str) -> Optional[SchoolModel]:
        """
        Retrieve a school from the database by its ICO.

        Args:
            ico (str): The unique identification number (IČO) of the school.

        Returns:
            Optional[School]: The school if found, None otherwise.
        """
        db = get_db_session()
        return (
            db.query(cls).filter(cls.ico == ico).first()._to_model()
            if db.query(cls).filter(cls.ico == ico).first()
            else None
        )

    @classmethod
    def create_new_school(cls, school_data: SchoolCreateModel) -> SchoolModel:
        """
        Create a new school in the database.

        This method performs the following steps:
        1. Creates a new School instance with the provided data
        2. Adds the new school to the database and commits the transaction

        Args:
            school_data (SchoolCreateModel): The data for creating the new school.

        Returns:
            School: The created school instance.

        Raises:
            CustomInternalServerErrorException: If there's an error during school creation.
        """
        db = get_db_session()
        try:
            new_school = cls(**school_data.dict())
            db.add(new_school)
            db.commit()
            db.refresh(new_school)
            return new_school._to_model()
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating new school: {str(e)}")
            raise CustomInternalServerErrorException(
                ResponseMessages.SCHOOL_CREATION_FAILED
            )
