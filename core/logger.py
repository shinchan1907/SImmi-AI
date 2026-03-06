import logging
import sys
from pathlib import Path
import structlog
from rich.logging import RichHandler

def setup_logging(log_level: str = "INFO"):
    """
    Configure structured logging with Rich terminal output and file logging.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
    ]

    # Terminal output processors
    terminal_processors = processors + [
        structlog.dev.ConsoleRenderer()
    ]

    # JSON file output processors
    file_processors = processors + [
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Standard library logging setup
    handler = RichHandler(rich_tracebacks=True, markup=True)
    file_handler = logging.FileHandler(log_dir / "simmi.log")
    
    # Formatter for file (JSON)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=processors,
        processors=[structlog.processors.JSONRenderer()],
    )
    file_handler.setFormatter(file_formatter)

    # Formatter for terminal (Rich)
    terminal_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=processors,
        processors=[structlog.dev.ConsoleRenderer()],
    )
    handler.setFormatter(terminal_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

def get_logger(name: str):
    return structlog.get_logger(name)
