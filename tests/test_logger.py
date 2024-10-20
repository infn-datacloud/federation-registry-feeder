from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, Logger

from pytest_cases import parametrize, parametrize_with_cases

from src.logger import StderrFilter, StdoutFilter, create_logger
from tests.utils import random_lower_string


class CaseLevel:
    @parametrize(level=(NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL))
    def case_level(self, level: int) -> int:
        return level


def test_logger() -> None:
    name = random_lower_string()
    logger = create_logger(name)
    assert isinstance(logger, Logger)
    assert logger.name == name
    assert logger.level == NOTSET
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0].filters[0], StdoutFilter)
    assert isinstance(logger.handlers[1].filters[0], StderrFilter)


@parametrize_with_cases("level", cases=CaseLevel)
def test_level(level: int) -> None:
    logger = create_logger(random_lower_string(), level)
    assert logger.level == level


def test_invalid_level(caplog) -> None:
    level = random_lower_string()
    logger = create_logger(random_lower_string(), level)
    assert logger.level == NOTSET
    assert f"Invalid log level: {level}" in caplog.text


def test_stdout_filter(capsys) -> None:
    logger = create_logger(random_lower_string(), DEBUG)
    logger.debug("debug")
    logger.warning("warning")
    logger.info("info")
    logger.error("error")
    logger.critical("critical")
    captured = capsys.readouterr()
    assert "debug" in captured.out
    assert "warning" in captured.out
    assert "info" in captured.out
    assert "error" in captured.err
    assert "critical" in captured.err
