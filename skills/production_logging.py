"""
Production Logging Utility

Centralized logging system for the Enterprise AI Employee.
Provides structured logging, log rotation, and multi-destination support.

Features:
- Structured JSON logging
- Log rotation by size and age
- Multiple log destinations (file, console)
- Log level filtering
- Context tracking
- Performance metrics

Usage:
    from skills.production_logging import get_logger, ProductionLogger
    
    logger = get_logger("my_component")
    logger.info("Action started", extra={"user_id": "123"})
    logger.error("Action failed", extra={"error": "details"})
"""

import os
import json
import logging
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


# ============================================================
# Configuration
# ============================================================

LOGS_DIR = "Logs"
ARCHIVE_DIR = os.path.join(LOGS_DIR, "Archive")

# Log rotation settings
MAX_LOG_SIZE_MB = 10  # Rotate after 10 MB
BACKUP_COUNT = 5  # Keep 5 backup files
LOG_RETENTION_DAYS = 30  # Keep logs for 30 days

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}


# ============================================================
# Structured Log Formatter
# ============================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter.
    
    Produces logs in JSON format for easy parsing and analysis.
    """
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if requested
        if self.include_extra:
            extra_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in {
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'message', 'asctime'
                }
            }
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter.
    
    Produces logs in traditional text format for human reading.
    """
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )


# ============================================================
# Production Logger
# ============================================================

class ProductionLogger:
    """
    Production-grade logger with rotation and multiple destinations.
    
    Features:
    - File rotation by size
    - Time-based rotation
    - Multiple log levels
    - Structured and human-readable formats
    - Archive management
    """
    
    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        level: str = "INFO",
        console_output: bool = True,
        structured_logs: bool = False
    ):
        """
        Initialize production logger.
        
        Args:
            name: Logger name
            log_file: Log file path (default: Logs/{name}.log)
            level: Log level
            console_output: Enable console output
            structured_logs: Use JSON format
        """
        self.name = name
        self.level = LOG_LEVELS.get(level.upper(), logging.INFO)
        self.console_output = console_output
        self.structured_logs = structured_logs
        
        # Determine log file path
        if log_file is None:
            log_file = os.path.join(LOGS_DIR, f"{name}.log")
        
        self.log_file = log_file
        
        # Ensure directories exist
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Add handlers
        self._add_file_handler()
        if console_output:
            self._add_console_handler()
    
    def _add_file_handler(self):
        """Add rotating file handler."""
        try:
            # Size-based rotation
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            
            # Set formatter
            if self.structured_logs:
                formatter = StructuredFormatter()
            else:
                formatter = HumanReadableFormatter()
            
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.level)
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")
    
    def _add_console_handler(self):
        """Add console handler."""
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(HumanReadableFormatter())
            console_handler.setLevel(self.level)
            
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Warning: Could not create console handler: {e}")
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, extra=kwargs)
    
    def log_action(
        self,
        action: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an action with structured data.
        
        Args:
            action: Action name
            status: Action status
            details: Action details
        """
        log_data = {
            "action": action,
            "status": status
        }
        if details:
            log_data["details"] = details
        
        level = "info" if status == "success" else "error"
        getattr(self, level)(f"{action} - {status}", **log_data)


# ============================================================
# Log Management
# ============================================================

class LogManager:
    """
    Manages log files including rotation, archiving, and cleanup.
    """
    
    def __init__(self, logs_dir: str = LOGS_DIR):
        self.logs_dir = logs_dir
        self.archive_dir = os.path.join(logs_dir, "Archive")
        
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
    
    def rotate_logs(self, max_age_days: int = LOG_RETENTION_DAYS):
        """
        Rotate and archive old log files.
        
        Args:
            max_age_days: Maximum age of logs to keep
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for filename in os.listdir(self.logs_dir):
            if not filename.endswith('.log'):
                continue
            
            filepath = os.path.join(self.logs_dir, filename)
            
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if mtime < cutoff_date:
                    # Archive old log
                    self._archive_log(filepath)
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    def _archive_log(self, filepath: str):
        """
        Archive a log file.
        
        Args:
            filepath: Path to log file
        """
        try:
            filename = os.path.basename(filepath)
            archive_name = f"{filename}.{datetime.now().strftime('%Y%m%d%H%M%S')}.gz"
            archive_path = os.path.join(self.archive_dir, archive_name)
            
            # Compress and archive
            with open(filepath, 'rb') as f_in:
                with gzip.open(archive_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original
            os.remove(filepath)
            
            print(f"Archived: {filename} -> {archive_name}")
            
        except Exception as e:
            print(f"Error archiving {filepath}: {e}")
    
    def cleanup_archives(self, max_age_days: int = 90):
        """
        Clean up old archived logs.
        
        Args:
            max_age_days: Maximum age of archives to keep
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for filename in os.listdir(self.archive_dir):
            if not filename.endswith('.gz'):
                continue
            
            filepath = os.path.join(self.archive_dir, filename)
            
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if mtime < cutoff_date:
                    os.remove(filepath)
                    print(f"Deleted old archive: {filename}")
                    
            except Exception as e:
                print(f"Error processing archive {filename}: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get log file statistics.
        
        Returns:
            Dictionary with log statistics
        """
        stats = {
            "active_logs": [],
            "archived_logs": [],
            "total_size_mb": 0,
            "archive_size_mb": 0
        }
        
        # Active logs
        for filename in os.listdir(self.logs_dir):
            if not filename.endswith('.log'):
                continue
            
            filepath = os.path.join(self.logs_dir, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            stats["active_logs"].append({
                "name": filename,
                "size_mb": round(size_mb, 2),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(filepath)
                ).isoformat()
            })
            stats["total_size_mb"] += size_mb
        
        # Archived logs
        for filename in os.listdir(self.archive_dir):
            if not filename.endswith('.gz'):
                continue
            
            filepath = os.path.join(self.archive_dir, filename)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            stats["archived_logs"].append({
                "name": filename,
                "size_mb": round(size_mb, 2)
            })
            stats["archive_size_mb"] += size_mb
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["archive_size_mb"] = round(stats["archive_size_mb"], 2)
        
        return stats


# ============================================================
# Module Exports
# ============================================================

# Global logger registry
_loggers: Dict[str, ProductionLogger] = {}


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "INFO",
    console_output: bool = False,
    structured_logs: bool = False
) -> ProductionLogger:
    """
    Get or create a named logger.
    
    Args:
        name: Logger name
        log_file: Log file path
        level: Log level
        console_output: Enable console output
        structured_logs: Use JSON format
        
    Returns:
        ProductionLogger instance
    """
    if name not in _loggers:
        _loggers[name] = ProductionLogger(
            name=name,
            log_file=log_file,
            level=level,
            console_output=console_output,
            structured_logs=structured_logs
        )
    
    return _loggers[name]


def get_log_manager() -> LogManager:
    """Get log manager instance."""
    return LogManager()


# Default logger for module-level logging
default_logger = get_logger("enterprise")


def log_action(component: str, action: str, status: str, details: Dict[str, Any] = None):
    """
    Log an action using the default logger.
    
    Args:
        component: Component name
        action: Action name
        status: Action status
        details: Action details
    """
    logger = get_logger(component)
    logger.log_action(action, status, details)


__all__ = [
    'ProductionLogger',
    'LogManager',
    'StructuredFormatter',
    'HumanReadableFormatter',
    'get_logger',
    'get_log_manager',
    'log_action',
    'default_logger',
    'LOG_LEVELS'
]
