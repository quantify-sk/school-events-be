import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Generator, Optional, Type

import bcrypt
from app.core.config import settings
from app.database import Base, SessionLocal
from app.logger import logger
from app.models.user import UserTokenData
from app.utils.exceptions import CustomAuthException
from fastapi import Depends
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

# OAuth2 settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

# OAuth2 schemes
oauth2_user_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login_user/")
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy database session.
    Rolls back the transaction if an exception occurs or if `context_set_db_session_rollback` is set.
    """
    from app.context_manager import context_set_db_session_rollback

    db: Session = SessionLocal()
    context_set_db_session_rollback.set(False)  # Ensure the default value is set

    try:
        yield db

        if context_set_db_session_rollback.get():
            logger.info("Rollback db session")
            db.rollback()
        else:
            db.commit()
    except (OperationalError, DBAPIError) as e:
        logger.error(f"Database error encountered: {e}")
        db.rollback()  # Ensure rollback on database errors
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"General exception in DB session: {e}")
        raise e
    finally:
        db.close()


def generate_random_id(length: int = 9) -> str:
    """
    Generate a random alphanumeric ID of a specified length.

    Args:
        length (int): Length of the random ID to be generated. Default is 9.

    Returns:
        str: Random alphanumeric ID.
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create an access token with optional expiration delta.

    Args:
        data (dict): Data to encode in the token.
        expires_delta (Optional[timedelta]): Expiration delta. Default is settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a refresh token with optional expiration delta.

    Args:
        data (dict): Data to encode in the token.
        expires_delta (Optional[timedelta]): Expiration delta. Default is settings.REFRESH_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT refresh token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user_token(token: str = Depends(oauth2_user_scheme)):
    """
    Decode the access token and set the user data in the context.

    Args:
        token (str): JWT access token.

    Raises:
        CustomAuthException: If token is invalid or decoding fails.
    """
    from app.context_manager import context_actor_user_data

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        context_actor_user_data.set(UserTokenData(**payload))
    except JWTError as e:
        logger.info(f"Error while decoding access token: {e}")
        raise CustomAuthException()


def get_password_hash(password: str) -> str:
    """
    Generate a password hash for the given password.

    Args:
        password (str): The password to hash.

    Returns:
        str: The hashed password.
    """
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password to be verified.
        hashed_password (str): The hashed password to be compared against.

    Returns:
        bool: True if the plain password matches the hashed password, False otherwise.
    """
    password_byte_enc = plain_password.encode("utf-8")
    hashed_password_byte = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte)


def check_if_dict_contains_keys(dictionary: dict, keys: list) -> bool:
    """
    Check if a dictionary contains all the specified keys.

    Args:
        dictionary (dict): The dictionary to check.
        keys (list): The list of keys to check for.

    Returns:
        bool: True if the dictionary contains all the keys, False otherwise.
    """
    return all(key in dictionary for key in keys)


def number_to_excel_column(n: int) -> str:
    """
    Convert a number to an Excel-style column name.

    Args:
        n (int): The number to convert.

    Returns:
        str: The Excel-style column name.
    """
    # Initialize the result list
    result = []

    # Convert the number to an Excel-style column name
    while n > 0:
        # Calculate the remainder of the division of n-1 by 26
        n, remainder = divmod(n - 1, 26)

        # Append the corresponding uppercase letter to the result list
        result.append(string.ascii_uppercase[remainder])

    # Reverse the result list and join it into a string
    return "".join(reversed(result))


def get_base_table_columns(
    model: Type[DeclarativeMeta],
) -> Dict[str, InstrumentedAttribute]:
    """
    Retrieve the columns of the base table for a given SQLAlchemy model class.

    This function identifies the base table of the provided model class and extracts
    its columns. It's particularly useful for operations that require direct access to
    the columns of the model's base table, bypassing any columns defined in derived classes.

    Args:
        model: The SQLAlchemy model class to inspect.

    Returns:
        A dictionary mapping column names to their respective SQLAlchemy `InstrumentedAttribute`
        objects if the base table is found. Returns an empty dictionary if the model does not
        inherit from any other model or if the base table cannot be determined.
    """
    # Get the base class of the model
    base_table = model.__base__

    # Check if the model is its own base class (no inheritance)
    if base_table == model:
        # No base class found, return an empty dictionary
        return {}

    # Check if the base class has a '__table__' attribute, indicating it maps to a database table
    if base_table and hasattr(base_table, "__table__"):
        # Extract and return the columns from the base table
        columns = base_table.__table__.columns
        return columns

    # If no base table is found, return an empty dictionary
    return {}


def serialize_timedelta(td: timedelta) -> str:
    """
    Serializes a timedelta object into a string representation of its total
    seconds.

    Args:
        td (timedelta): The timedelta object to be serialized.

    Returns:
        str: The string representation of the total seconds in the timedelta.
    """
    return str(td.total_seconds())


def get_base_table(model: Type[DeclarativeMeta]) -> Optional[Type[DeclarativeMeta]]:
    """
    Retrieve the base table class from a given model class.

    This function navigates the inheritance hierarchy to find the base table
    class for a given SQLAlchemy model class. The base table class is the one
    that directly maps to a table in the database, as indicated by having a
    `__table__` attribute.

    Args:
        model: The model class from which to retrieve the base table.

    Returns:
        The base table class if found, otherwise None.
    """
    # Get the base class of the model
    base_table = model.__base__

    # Check if the model is its own base class (no inheritance)
    if base_table == model:
        # The model does not inherit from any other class
        return None

    # Check if the base class has a '__table__' attribute, indicating it is a table-mapped class
    if base_table and hasattr(base_table, "__table__"):
        # The base class is the table-mapped class
        return base_table

    # No base table class was found
    return None


def get_model_class(table_name: str) -> Type[DeclarativeMeta]:
    """
    Get a SQLAlchemy model class from its table name.

    Args:
        table_name (str): The name of the table.

    Returns:
        The SQLAlchemy model class corresponding to the table name, or None if not found.
    """
    # Iterate over all classes registered in the Base declarative base
    for cls in Base.registry._class_registry.values():
        if hasattr(cls, "__tablename__") and cls.__tablename__ == table_name:
            return cls
    return None
