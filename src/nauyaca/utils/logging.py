"""Logging configuration for Nauyaca.

This module provides structured logging configuration using structlog.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any

import structlog


def hash_ip_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Hash IP addresses in log events for privacy.

    Per Gemini application best practices, IP addresses should be hashed
    in logs to protect user privacy while still allowing abuse detection.

    Args:
        logger: The logger instance.
        method_name: The logging method name.
        event_dict: The event dictionary.

    Returns:
        The event dictionary with client_ip replaced by client_ip_hash.
    """
    if "client_ip" in event_dict:
        ip = event_dict["client_ip"]
        if ip and ip != "unknown":
            # SHA256 hash, truncated to 12 chars for readability
            hashed = hashlib.sha256(ip.encode()).hexdigest()[:12]
            event_dict["client_ip_hash"] = hashed
            del event_dict["client_ip"]
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_logs: bool = False,
    hash_ips: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file. If None, logs to stdout.
        json_logs: If True, output logs in JSON format. Otherwise, use
            human-readable format.
        hash_ips: If True (default), hash client IP addresses in logs
            for privacy per Gemini application best practices.

    Examples:
        >>> # Configure for development (human-readable console output)
        >>> configure_logging(log_level="DEBUG")

        >>> # Configure for production (JSON logs to file, hashed IPs)
        >>> configure_logging(
        ...     log_level="INFO",
        ...     log_file=Path("/var/log/nauyaca.log"),
        ...     json_logs=True,
        ...     hash_ips=True
        ... )
    """
    # Determine output stream
    if log_file:
        output_stream = open(log_file, "a")
    else:
        output_stream = sys.stdout

    # Build base processors
    base_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso" if json_logs else "%Y-%m-%d %H:%M:%S"),
    ]

    # Add IP hashing processor if enabled (for privacy)
    if hash_ips:
        base_processors.append(hash_ip_processor)

    # Configure output format
    if json_logs:
        # JSON format for production/structured logging
        processors = base_processors + [structlog.processors.JSONRenderer()]
    else:
        # Human-readable format for development
        processors = base_processors + [
            structlog.dev.ConsoleRenderer(colors=output_stream.isatty())
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
