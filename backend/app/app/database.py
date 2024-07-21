from threading import Lock

from app.core.config import settings
from app.logger import logger
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import sessionmaker

# Configuration variables
DB_POOL_SIZE = 83
WEB_CONCURRENCY = 9
POOL_SIZE = max(DB_POOL_SIZE // WEB_CONCURRENCY, 5)

# Initialize lock and engine variables
connection_pool_lock = Lock()
engine = None


def get_database_engine():
    """
    Returns a SQLAlchemy engine, creating it if it doesn't exist based on the URI provided.
    If no URI is provided, uses the default DATABASE_URI from settings.
    """
    global engine
    uri = settings.DATABASE_URI

    with connection_pool_lock:
        if engine is None:
            engine = create_engine(
                uri,
                poolclass=pool.QueuePool,
                pool_pre_ping=True,
                pool_size=30,  # Number of connections to be kept open in the pool
                max_overflow=50,  # Maximum number of connections that can be opened if the pool is exhausted
                pool_recycle=900,  # Time in seconds after which a connection is automatically recycled
            )
            logger.info("Created new database engine.")
        else:
            logger.info("Reusing existing database engine.")

    return engine


# Create a session factory with a dynamic engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_database_engine(),  # Dynamically bind to the engine
)


@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate a lowercase table name automatically from the class name.
        """
        return cls.__name__.lower()
