"""
Structured logging utility for the backend application.

Provides consistent, colored console logging with configurable levels.
Uses Python's built-in logging module, wired to the application settings.

Usage:
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.debug("Processing request")
    logger.info("User authenticated", extra={"user": "0x123..."})
    logger.warning("Slow query detected")
    logger.error("Database connection failed")
"""

import logging
import sys
from typing import Optional

# ANSI color codes for terminal output
COLORS = {
    "DEBUG": "\033[90m",    # Gray
    "INFO": "\033[94m",     # Blue
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",    # Red
    "CRITICAL": "\033[95m", # Magenta
    "RESET": "\033[0m",     # Reset
}


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels in terminal output.
    """

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, use_colors: bool = True):
        super().__init__(self.FORMAT, datefmt=self.DATE_FORMAT)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Save original level name
        original_levelname = record.levelname

        # Apply color if enabled
        if self.use_colors and record.levelname in COLORS:
            record.levelname = (
                f"{COLORS[record.levelname]}{record.levelname}{COLORS['RESET']}"
            )

        # Format the message
        result = super().format(record)

        # Restore original level name
        record.levelname = original_levelname

        return result


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure the root logger for the application.

    Should be called once at application startup (in main.py lifespan).

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
               If not provided, reads from settings.
    """
    # Import here to avoid circular imports
    from src.config import get_settings

    settings = get_settings()
    log_level = level or settings.log_level

    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Use colors if outputting to a terminal
    use_colors = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    formatter = ColoredFormatter(use_colors=use_colors)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    # Only log errors for access logs (no 200 OK spam)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name, typically __name__

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
    """
    return logging.getLogger(name)
