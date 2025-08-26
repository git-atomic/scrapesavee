"""
Production-grade logging configuration for ScrapeSavee Worker
Provides structured logging with JSON format, proper levels, and performance monitoring
"""
import sys
import logging
import logging.config
from typing import Dict, Any
from datetime import datetime
import json

from .config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        
        # Add context fields
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "source_id"):
            log_entry["source_id"] = record.source_id
        if hasattr(record, "item_id"):
            log_entry["item_id"] = record.item_id
        if hasattr(record, "run_id"):
            log_entry["run_id"] = record.run_id
        
        # Add performance metrics if present
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "memory_mb"):
            log_entry["memory_mb"] = record.memory_mb
        
        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record"""
        # Add service info
        record.service = settings.APP_NAME
        record.version = settings.VERSION
        record.environment = "production" if not settings.DEBUG else "development"
        
        return True


def setup_logging(name: str = None) -> logging.Logger:
    """
    Setup production-grade logging configuration
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    
    # Logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {
            "context": {
                "()": ContextFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "structured" if not settings.DEBUG else "simple",
                "filters": ["context"],
                "level": settings.LOG_LEVEL,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "structured",
                "filters": ["context"],
                "level": "ERROR",
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "formatter": "structured",
                "filters": ["context"],
                "level": settings.LOG_LEVEL,
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "app_file", "error_file"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"] if settings.DEBUG else ["app_file"],
                "level": "INFO" if settings.DEBUG else "WARNING",
                "propagate": False,
            },
            "aio_pika": {
                "handlers": ["console"] if settings.DEBUG else ["app_file"],
                "level": "INFO",
                "propagate": False,
            },
            "crawl4ai": {
                "handlers": ["console"] if settings.DEBUG else ["app_file"],
                "level": "WARNING",
                "propagate": False,
            },
            "playwright": {
                "handlers": ["console"] if settings.DEBUG else ["app_file"],
                "level": "WARNING",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Get logger
    logger_name = name if name else "app"
    logger = logging.getLogger(logger_name)
    
    return logger


class PerformanceLogger:
    """Context manager for performance logging"""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        self.logger.info(f"Starting {self.operation}", extra={"extra_fields": self.context})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        import psutil
        
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                extra={
                    "extra_fields": {
                        **self.context,
                        "duration_ms": round(duration_ms, 2),
                        "memory_mb": round(memory_mb, 2),
                    }
                }
            )
        else:
            self.logger.error(
                f"Failed {self.operation}: {exc_val}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        **self.context,
                        "duration_ms": round(duration_ms, 2),
                        "memory_mb": round(memory_mb, 2),
                    }
                }
            )


def get_logger(name: str = None) -> logging.Logger:
    """Get a configured logger instance"""
    return setup_logging(name)


# Export commonly used items
__all__ = [
    "setup_logging",
    "get_logger", 
    "PerformanceLogger",
    "StructuredFormatter",
    "ContextFilter"
]
