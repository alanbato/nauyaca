"""Logging configuration for Nauyaca.

This module provides structured logging configuration using structlog.
"""

import sys
from pathlib import Path

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file. If None, logs to stdout.
        json_logs: If True, output logs in JSON format. Otherwise, use
            human-readable format.

    Examples:
        >>> # Configure for development (human-readable console output)
        >>> configure_logging(log_level="DEBUG")

        >>> # Configure for production (JSON logs to file)
        >>> configure_logging(
        ...     log_level="INFO",
        ...     log_file=Path("/var/log/nauyaca.log"),
        ...     json_logs=True
        ... )
    """
    # Determine output stream
    if log_file:
        output_stream = open(log_file, "a")
    else:
        output_stream = sys.stdout

    # Configure processors based on format
    if json_logs:
        # JSON format for production/structured logging
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable format for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=output_stream.isatty()),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(_level_to_int(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output_stream),
        cache_logger_on_first_use=True,
    )


def _level_to_int(level: str) -> int:
    """Convert string log level to integer.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Integer log level.
    """
    levels = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    return levels.get(level.upper(), 20)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__).

    Returns:
        A structlog BoundLogger instance.

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("server_started", host="localhost", port=1965)
    """
    return structlog.get_logger(name)
