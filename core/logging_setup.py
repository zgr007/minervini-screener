"""
Minervini Screener v1.0 - Structured Logging Setup
Provides structlog-based logging with JSON and console output support.
"""
import sys
import structlog
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "console",
    log_file: Optional[str] = None,
) -> None:
    """Configure structlog with console or JSON output.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_format: "console" for colored human output, "json" for structured JSON
        log_file: Optional path to log file (appended to, never rotated here)
    """
    # Set up standard logging to structlog bridge
    import logging
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                force_colors=True,
            )
        )

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Optional file logging
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(file_path), encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logging.getLogger().addHandler(file_handler)

    logger = get_logger(__name__)
    logger.info(
        "日志系统已初始化",
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Usually __name__ of the calling module

    Returns:
        A structlog BoundLogger
    """
    return structlog.get_logger(name)
