"""
Personal AI Employee - Logging & Audit System
Dual output: console + rotating file logs with structured audit trail.
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from config import config, LOGS_DIR, ensure_folders

# Ensure log directories exist
ensure_folders()

# Log file paths
SYSTEM_LOG = LOGS_DIR / "system.log"
AUDIT_LOG = LOGS_DIR / "audit.jsonl"
TASK_LOG_DIR = LOGS_DIR / "tasks"
TASK_LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for audit trail."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "user"):
            log_entry["user"] = record.user
        return json.dumps(log_entry)


def setup_logger(name: str = "ai_employee", level: str | None = None) -> logging.Logger:
    """Create a logger with console + file handlers."""
    logger = logging.getLogger(name)
    log_level = level or config.log_level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        SYSTEM_LOG, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(console_fmt)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logger()


def audit_log(
    action: str,
    level: str = "INFO",
    task_id: str | None = None,
    user: str | None = None,
    details: dict | None = None,
):
    """Write structured audit entry to JSONL file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "action": action,
        "task_id": task_id,
        "user": user,
        "details": details or {},
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def task_logger(task_id: str) -> logging.Logger:
    """Create a dedicated logger for a specific task."""
    tl = logging.getLogger(f"task.{task_id}")
    if not tl.handlers:
        tl.setLevel(logging.DEBUG)
        task_log_file = TASK_LOG_DIR / f"{task_id}.log"
        fh = RotatingFileHandler(task_log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s"))
        tl.addHandler(fh)
    return tl


def log_system_event(level: str, message: str, component: str = "system"):
    """Convenience for system-level logging."""
    audit_log(action=message, level=level, details={"component": component})
    getattr(logger, level.lower(), logger.info)(f"[{component}] {message}")
