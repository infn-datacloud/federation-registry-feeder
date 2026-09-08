import logging
import sys
import threading
from logging import Formatter, Handler, Logger, LogRecord, StreamHandler


class ErrorDetailsHandler(Handler):
    """Collect error log details emitted during the current execution."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self._records: list[str] = []
        self._lock = threading.Lock()
        self.setFormatter(Formatter("%(levelname)s - %(name)s - %(message)s"))

    def emit(self, record: LogRecord) -> None:
        detail = self.format(record)
        with self._lock:
            self._records.append(detail)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def details(self) -> str:
        """Return stable details, independent of parallel logging order."""
        with self._lock:
            records = sorted(self._records)
        return "\n".join(records)


error_details_handler = ErrorDetailsHandler()


def start_error_capture() -> None:
    """Start a fresh error capture on the root logger."""
    error_details_handler.reset()
    root_logger = logging.getLogger()
    if error_details_handler not in root_logger.handlers:
        root_logger.addHandler(error_details_handler)


def get_error_details() -> str:
    """Return the errors captured during the current execution."""
    return error_details_handler.details()


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
