from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class SchoolModel(BaseModel):
    """
    Pydantic model representing a school.

    This model is used for serialization and deserialization of school data.

    Attributes:
        id (int): The unique identifier for the school.
        name (str): The name of the school.
        ico (str): A unique identification number for the school (IČO).
        address (str): The address of the school.
        district (str): The district (okres) where the school is located.
        region (str): The region (kraj) where the school is located.
        created_at (datetime): Timestamp of when the school record was created.
        updated_at (datetime): Timestamp of the last update to the school record.
        representatives (Optional[List[UserModel]]): List of school representatives (optional).
    """

    id: int
    name: str
    ico: str = Field(..., description="IČO (Identification number)")
    address: str
    district: str
    region: str
    created_at: datetime
    updated_at: datetime
    representatives: Optional[List["UserModel"]] = None
    number_of_students: Optional[int] = 0
    number_of_employees: Optional[int] = 0
    psc: Optional[str] = None
    city: Optional[str] = None

    class Config:
        from_attributes = True

    def build_school_token_data(self) -> "SchoolTokenData":
        """
        Create a SchoolTokenData instance from this SchoolModel.

        Returns:
            SchoolTokenData: An instance containing the school's ID for token generation.
        """
        return SchoolTokenData(
            school_id=self.id,
        )


class SchoolTokenData(BaseModel):
    """
    Pydantic model for school data to be included in a token.

    Attributes:
        school_id (int): The unique identifier for the school.
    """

    school_id: int


class SchoolCreateModel(BaseModel):
    """
    Pydantic model for creating a new school.

    Attributes:
        name (str): The name of the school.
        ico (str): A unique identification number for the school (IČO).
        address (str): The address of the school.
        district (str): The district (okres) where the school is located.
        region (str): The region (kraj) where the school is located.
    """

    name: str
    ico: str = Field(..., description="IČO (Identification number)")
    address: str
    district: str
    region: str
    number_of_students: Optional[int] = 0
    number_of_employees: Optional[int] = 0
    psc: Optional[str] = None
    city: Optional[str] = None


class SchoolUpdateModel(BaseModel):
    """
    Pydantic model for updating an existing school.

    All fields are optional, allowing partial updates.

    Attributes:
        name (Optional[str]): The name of the school.
        ico (Optional[str]): A unique identification number for the school (IČO).
        address (Optional[str]): The address of the school.
        district (Optional[str]): The district (okres) where the school is located.
        region (Optional[str]): The region (kraj) where the school is located.
    """

    name: Optional[str] = None
    ico: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    number_of_students: Optional[int] = None
    number_of_employees: Optional[int] = None


# This import is used for type hinting purposes only
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import UserModel
