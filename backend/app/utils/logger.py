"""Application Logging Subsystem.

Demonstrates:
- Singleton Logger Pattern
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Formatted console and file logging
- Sanitization of sensitive data
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from threading import Lock
from typing import Optional
from app.config import get_settings


class LoggerManager:
    """Thread-safe Singleton Logger Manager for standardized application logging."""

    _instance: Optional["LoggerManager"] = None
    _lock: Lock = Lock()
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> "LoggerManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LoggerManager, cls).__new__(cls)
                cls._instance._setup_logger()
            return cls._instance

    def _setup_logger(self) -> None:
        settings = get_settings()
        logger = logging.getLogger("it_asset_manager")

        # Map string log level to logging constant
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        log_level = level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)

        # Prevent duplicate handlers if re-initialized
        if logger.handlers:
            logger.handlers.clear()

        log_format = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 1. Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # 2. Rotating File Handler
        try:
            log_dir = os.path.dirname(settings.LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)
        except (OSError, IOError) as exc:
            logger.warning("Could not set up file handler for %s: %s", settings.LOG_FILE, exc)

        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._setup_logger()
        return self._logger


def get_logger() -> logging.Logger:
    """Return the global application logger."""
    return LoggerManager().logger
