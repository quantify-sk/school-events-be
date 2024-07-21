import logging
from logging.handlers import TimedRotatingFileHandler


def get_logger(name, level=logging.DEBUG) -> logging.Logger:
    """Logging setup with TimedRotatingFileHandler."""

    logger_instance = logging.getLogger(name)
    logger_instance.propagate = (
        False  # Prevent the logger from propagating messages to the root logger
    )

    # Setup only if no handlers are associated with this logger, to avoid duplicate handlers
    if not logger_instance.handlers:
        log_handler = TimedRotatingFileHandler(
            filename="/logs/all.log",  # Ensure the path exists and is writable
            when="midnight",
            interval=1,
            backupCount=60,  # Keep last 60 days of logs
            encoding="utf-8",
        )
        log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s loglevel=%(levelname)-6s logger=%(name)-25s %(funcName)s() L%(lineno)-4d %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger_instance.addHandler(log_handler)

    logger_instance.setLevel(level)
    return logger_instance


logger = get_logger(__name__)
logger.info("Logger initiated")
