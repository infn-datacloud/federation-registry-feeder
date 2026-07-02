import logging
import sys
import threading
from logging import Formatter, Logger, StreamHandler


class StdoutFilter(logging.Filter):
    def filter(self, record):
        return record.levelno <= logging.WARNING


class StderrFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.ERROR


def thread_id_filter(record):
    """Inject thread_id to log records"""
    record.thread_id = threading.get_native_id()
    return record


def create_logger(name: str, level: str | int | None = None) -> Logger:
    """Create a logger with 2 stream handlers.

    Log to stdout messages with level lower or equal then WARNING otherwise log them
    to stderr.
    """
    logger = logging.getLogger(name)
    try:
        if level is not None:
            logger.setLevel(level)
        error_msg = None
    except ValueError:
        error_msg = f"Invalid log level: {level}"
    formatter = Formatter(
        "%(asctime)s - %(levelname)s - %(thread_id)d - %(name)s - %(message)s"
    )

    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(thread_id_filter)
    stdout_handler.addFilter(StdoutFilter())
    logger.addHandler(stdout_handler)

    stderr_handler = StreamHandler()
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(thread_id_filter)
    stderr_handler.addFilter(StderrFilter())
    logger.addHandler(stderr_handler)

    if error_msg is not None:
        logger.error(error_msg)

    return logger
