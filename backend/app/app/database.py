from threading import Lock
from sqlalchemy import create_engine, pool, event, exc
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import sessionmaker
import os
from app.core.config import settings
from app.logger import logger

# Initialize lock and engine variables
connection_pool_lock = Lock()
engine = None


def create_new_engine(uri: str):
    """Helper function to create a new SQLAlchemy engine."""
    new_engine = create_engine(
        uri,
        poolclass=pool.QueuePool,
        pool_pre_ping=True,
        pool_size=30,
        max_overflow=50,
        pool_recycle=900,
    )

    # Attach event listeners to handle process-based disconnections
    @event.listens_for(new_engine, "connect")
    def connect(dbapi_connection, connection_record):
        connection_record.info["pid"] = os.getpid()

    @event.listens_for(new_engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        pid = os.getpid()
        if connection_record.info["pid"] != pid:
            connection_record.dbapi_connection = connection_proxy.dbapi_connection = (
                None
            )
            raise exc.DisconnectionError(
                f"Connection record belongs to pid {connection_record.info['pid']}, "
                f"attempting to check out in pid {pid}"
            )

    return new_engine


def get_database_engine():
    global engine
    uri = settings.DATABASE_URI

    with connection_pool_lock:
        if engine is None:
            engine = create_new_engine(uri)
            logger.info("Created new database engine.")
        else:
            try:
                # Test the existing engine connection
                with engine.connect():
                    pass
                logger.info("Reusing existing database engine.")
            except (OperationalError, DBAPIError):
                logger.warning("Database connection was lost. Recreating the engine.")
                engine.dispose()
                engine = create_new_engine(uri)
                logger.info("Created new database engine after reconnection.")

    return engine


# Create a session factory with a dynamically bound engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_database_engine(),
)


@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate a lowercase table name automatically from the class name."""
        return cls.__name__.lower()
