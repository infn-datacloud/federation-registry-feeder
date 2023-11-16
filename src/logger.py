import logging

logger = logging.getLogger("Federation Registry populator")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(handler)
