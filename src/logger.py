import logging
import sys
from logging import Formatter, Logger, StreamHandler


class StdoutFilter(logging.Filter):
    def filter(self, record):
        return record.levelno <= logging.WARNING


class StderrFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.ERROR


def create_logger(name: str, level: str) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(StdoutFilter())
    logger.addHandler(stdout_handler)

    stderr_handler = StreamHandler()
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(StderrFilter())
    logger.addHandler(stderr_handler)

    return logger
