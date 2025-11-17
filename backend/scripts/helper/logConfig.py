import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str):
    """
    Creates a custom logger that logs to a separate file for each module.
    
    :param name: Name of the module (used for log filename)
    :return: Configured logger instance
    """
    log_file = os.path.join(LOG_DIR, f"{name}.log")

    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Formatter for logs
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(module)s - %(message)s"
    )

    # File handler (rotating logs, max 5MB per file, 3 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(formatter)

    # Console handler (for debugging)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Attach handlers if not already added
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
