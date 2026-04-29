"""Structured logging configuration.

Uses structlog for JSON-formatted, structured log output that
integrates cleanly with Google Cloud Logging.
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog for the application.

    In Cloud Run, logs are automatically picked up by Cloud Logging
    when output as structured JSON to stdout.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # Use JSON in production, pretty console locally
            structlog.dev.ConsoleRenderer()
            if sys.stdout.isatty()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named structlog logger.

    Args:
        name: Logger name, typically __name__ of the module.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)
