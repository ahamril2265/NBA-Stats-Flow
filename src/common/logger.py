import logging
import os
from datetime import datetime


LOG_DIR = "logs"
LOG_LEVEL = logging.INFO


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with both console and file handlers.
    Ensures no duplicate handlers are added.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler
    log_file = os.path.join(
        LOG_DIR, f"{name.lower()}_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
