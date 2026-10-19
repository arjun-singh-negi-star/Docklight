import logging
import sys

from app.config import get_settings


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(settings.LOG_LEVEL.upper())
    return logger
