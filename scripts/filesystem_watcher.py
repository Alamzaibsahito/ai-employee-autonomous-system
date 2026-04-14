"""
Filesystem Watcher — Monitors configured directories for new/modified files.
Uses watchdog library for OS-level file system events.
Creates tasks when new files appear in watched directories.
"""

import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log

# Directories to watch (extend as needed)
DEFAULT_WATCH_DIRS = [
    Path.home() / "Downloads",
    FOLDERS["inbox"],  # Also watch our own inbox for external changes
]


class FileChangeHandler(FileSystemEventHandler):
    """Handle file system events and create tasks."""

    def __init__(self):
        super().__init__()
        self.processed_files = set()

    def _file_key(self, path: str) -> str:
        """Create unique key for file based on path + content hash."""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()[:4096]).hexdigest()
        except (OSError, PermissionError):
            return path

    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return

        path = str(event.src_path)
        file_key = self._file_key(path)

        if file_key in self.processed_files:
            return

        self.processed_files.add(file_key)
        self._create_task(path, "created")

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        path = str(event.src_path)
        # Only process modifications to files we care about
        if any(keyword in path.lower() for keyword in [".tmp", ".part", ".crdownload"]):
            return

        self._create_task(path, "modified")

    def _create_task(self, file_path: str, event_type: str):
        """Create a task file for the changed file."""
        task_id = f"FILE_{hashlib.md5(file_path.encode()).hexdigest()[:8].upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_file = FOLDERS["inbox"] / f"{task_id}.md"

        content = f"""---
task_id: {task_id}
source: filesystem_watcher
created: {datetime.now(timezone.utc).isoformat()}
status: inbox
priority: normal
file_path: {file_path}
event_type: {event_type}
---

# Task: File System Event Detected

**Source:** Filesystem Watcher
**File:** `{file_path}`
**Event:** {event_type}
**Time:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Action Required
> [!TODO] Review file change and determine if action is needed

## Notes
- Auto-created by Filesystem Watcher
- File path: {file_path}
"""
        try:
            with open(task_file, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Filesystem Watcher: Created task {task_id} for {event_type}: {file_path}")
            audit_log(
                action="filesystem_event",
                task_id=task_id,
                details={"file": file_path, "event": event_type},
            )
        except Exception as e:
            logger.error(f"Filesystem Watcher: Failed to create task file: {e}")


def run_filesystem_watcher(watch_dirs: list[Path] | None = None, poll_interval: int = 1):
    """Run filesystem watcher monitoring specified directories."""
    ensure_folders()

    dirs_to_watch = watch_dirs or DEFAULT_WATCH_DIRS
    event_handler = FileChangeHandler()
    observer = Observer()

    for dir_path in dirs_to_watch:
        if dir_path.exists():
            observer.schedule(event_handler, str(dir_path), recursive=False)
            logger.info(f"Filesystem Watcher: Watching {dir_path}")
        else:
            logger.warning(f"Filesystem Watcher: Directory not found, skipping: {dir_path}")

    observer.start()
    logger.info("Filesystem Watcher started")
    audit_log(action="filesystem_watcher_started", details={"watched_dirs": [str(d) for d in dirs_to_watch]})

    try:
        while True:
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logger.info("Filesystem Watcher: Shutting down")
        observer.stop()

    observer.join()


if __name__ == "__main__":
    run_filesystem_watcher()
