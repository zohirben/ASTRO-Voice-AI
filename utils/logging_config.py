"""
Structured Logging Configuration
Production-ready logging with structlog
"""

import logging
import structlog
from pathlib import Path
import sys

# Log directory
LOG_DIR = Path(__file__).parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)


def configure_logging(log_level: str = "INFO", log_to_file: bool = True):
    """
    Configure structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
    """
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if log_to_file else structlog.dev.ConsoleRenderer(),
    ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Add file handler if requested
    if log_to_file:
        file_handler = logging.FileHandler(
            LOG_DIR / "application.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter('%(message)s')
        )
        logging.getLogger().addHandler(file_handler)
    
    return structlog.get_logger()


def get_logger(name: str = None):
    """Get a logger instance"""
    return structlog.get_logger(name)


# Configure on import (can be overridden)
logger = configure_logging()
