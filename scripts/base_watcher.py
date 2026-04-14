"""
BaseWatcher — Abstract base class for all watchers in the Personal AI Employee system.
Provides common functionality for:
- Task file creation with standardized YAML frontmatter
- State management (load/save watcher state)
- Task lifecycle management (Inbox → Needs_Action → Done)
- Consistent error handling and audit logging

All watchers (Gmail, WhatsApp, Finance, Filesystem) should inherit from this class.
"""

import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Optional

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.
    Provides common task creation, state management, and lifecycle utilities.
    """

    def __init__(self, name: str, poll_interval: int = 60):
        """
        Initialize the base watcher.

        Args:
            name: Watcher name (e.g., 'gmail', 'whatsapp', 'finance')
            poll_interval: Seconds between polling cycles
        """
        self.name = name
        self.poll_interval = poll_interval
        self._running = False
        self.state_file = FOLDERS["logs"] / f"{self.name}_state.json"

        # Ensure required folders exist
        ensure_folders()

    # ─── Abstract Methods ──────────────────────────────────────────────

    @abstractmethod
    def check_for_events(self) -> int:
        """
        Implement watcher-specific logic to check for new events.
        Returns number of new tasks created.
        """
        pass

    # ─── Lifecycle ─────────────────────────────────────────────────────

    def start(self):
        """Start the watcher in continuous polling loop."""
        self._running = True
        logger.info(f"{self.name.capitalize()} Watcher started — polling every {self.poll_interval}s")
        audit_log(action=f"{self.name}_watcher_started", details={"poll_interval": self.poll_interval})

        while self._running:
            try:
                tasks = self.check_for_events()
                if tasks > 0:
                    logger.info(f"{self.name.capitalize()} Watcher: {tasks} new event(s) detected")
            except Exception as e:
                logger.error(f"{self.name.capitalize()} Watcher loop error: {e}")
                audit_log(
                    action=f"{self.name}_watcher_error",
                    level="ERROR",
                    details={"error": str(e)},
                )
            time.sleep(self.poll_interval)

    def stop(self):
        """Stop the watcher."""
        self._running = False
        logger.info(f"{self.name.capitalize()} Watcher stopping...")
        audit_log(action=f"{self.name}_watcher_stopped")

    # ─── State Management ──────────────────────────────────────────────

    def load_state(self, default: dict | None = None) -> dict:
        """Load watcher state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"{self.name} Watcher: Failed to load state: {e}")
        return default or {}

    def save_state(self, state: dict):
        """Save watcher state to JSON file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            logger.error(f"{self.name} Watcher: Failed to save state: {e}")

    def update_last_check(self, state: dict) -> dict:
        """Update the last_check timestamp in state."""
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        return state

    # ─── Task Creation ─────────────────────────────────────────────────

    def generate_task_id(self, prefix: str, unique_key: str) -> str:
        """
        Generate a unique task ID.

        Args:
            prefix: Task prefix (e.g., 'GMAIL', 'WA', 'FINANCE')
            unique_key: Unique identifier to hash (e.g., email_id, contact_name)

        Returns:
            Formatted task ID string
        """
        hash_val = hashlib.md5(unique_key.encode()).hexdigest()[:8].upper()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{hash_val}_{timestamp}"

    def create_task_file(
        self,
        task_id: str,
        metadata: dict,
        content: str,
        destination: str = "inbox",
    ) -> str:
        """
        Create a task markdown file with YAML frontmatter.

        Args:
            task_id: Unique task identifier
            metadata: Dict of YAML frontmatter fields
            content: Markdown content body (after frontmatter)
            destination: Target folder name ('inbox', 'needs_action', etc.)

        Returns:
            Path to created task file
        """
        # Ensure destination folder exists
        dest_folder = FOLDERS.get(destination)
        if not dest_folder:
            logger.error(f"Unknown destination folder: {destination}")
            dest_folder = FOLDERS["inbox"]

        task_file = dest_folder / f"{task_id}.md"

        # Build standardized YAML frontmatter
        # Always include these core fields
        frontmatter = {
            "task_id": metadata.get("task_id", task_id),
            "source": metadata.get("source", self.name),
            "created": metadata.get("created", datetime.now(timezone.utc).isoformat()),
            "status": metadata.get("status", destination),
            "priority": metadata.get("priority", "normal"),
        }

        # Add any additional metadata fields
        for key, value in metadata.items():
            if key not in frontmatter:
                frontmatter[key] = value

        # Write file with YAML frontmatter
        yaml_lines = []
        for key, value in frontmatter.items():
            # Handle special characters in values
            if isinstance(value, str) and any(c in value for c in [":", "{", "}", "[", "]", ",", "&", "*", "#", "?", "-", "<", ">", "=", "!", "%", "@", "`"]):
                yaml_lines.append(f"{key}: \"{value}\"")
            else:
                yaml_lines.append(f"{key}: {value}")

        yaml_block = "\n".join(yaml_lines)

        file_content = f"---\n{yaml_block}\n---\n\n{content}\n"

        try:
            with open(task_file, "w", encoding="utf-8") as f:
                f.write(file_content)

            logger.debug(f"Task file created: {task_file}")
            return str(task_file)

        except Exception as e:
            logger.error(f"Failed to create task file {task_file}: {e}")
            raise

    # ─── Task Lifecycle Management ─────────────────────────────────────

    def move_to_needs_action(
        self,
        task_id: str,
        metadata: dict,
        content: str,
        error_reason: str,
        retry_count: int = 0,
    ) -> str:
        """
        Move a task to Needs_Action folder (for failed/retry tasks).

        Args:
            task_id: Task identifier
            metadata: Task metadata
            content: Task content
            error_reason: Why the task needs action
            retry_count: Number of retry attempts

        Returns:
            Path to needs_action file
        """
        # Add error metadata
        metadata["status"] = "needs_action"
        metadata["error_reason"] = error_reason
        metadata["retry_count"] = retry_count
        metadata["last_error_at"] = datetime.now(timezone.utc).isoformat()

        # Add error note to content
        error_note = f"> [!ERROR] Task requires attention: {error_reason}\n"
        if retry_count > 0:
            error_note += f"> **Retry Attempt:** {retry_count}/{config.ralph_loop_max_retries}\n"

        full_content = f"{error_note}\n{content}"

        task_path = self.create_task_file(
            task_id=task_id,
            metadata=metadata,
            content=full_content,
            destination="needs_action",
        )

        audit_log(
            action="task_moved_to_needs_action",
            task_id=task_id,
            details={"error_reason": error_reason, "retry_count": retry_count},
        )

        logger.info(f"Task {task_id} moved to Needs_Action: {error_reason}")
        return task_path

    def move_to_done(self, task_id: str, source_path: str) -> Optional[str]:
        """
        Move a completed task to Done folder.

        Args:
            task_id: Task identifier
            source_path: Current path of task file

        Returns:
            Path to done file, or None if failed
        """
        try:
            source = Path(source_path)
            if not source.exists():
                logger.warning(f"Source task file not found: {source_path}")
                return None

            dest = FOLDERS["done"] / source.name

            # Read and update status
            content = source.read_text(encoding="utf-8")
            content = content.replace("status: inbox", "status: done")
            content = content.replace("status: pending_approval", "status: done")
            content = content.replace("status: needs_action", "status: done")

            # Add completion timestamp if not present
            if "completed:" not in content:
                completion_line = f"completed: {datetime.now(timezone.utc).isoformat()}"
                # Insert after first YAML block
                if "---" in content:
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = f"{parts[0]}---{parts[1]}---\ncompleted: {datetime.now(timezone.utc).isoformat()}\n{parts[2]}"

            dest.write_text(content, encoding="utf-8")
            source.unlink()

            audit_log(action="task_completed", task_id=task_id)
            logger.info(f"Task {task_id} moved to Done")
            return str(dest)

        except Exception as e:
            logger.error(f"Failed to move task {task_id} to Done: {e}")
            return None

    def move_to_approval(
        self,
        task_id: str,
        metadata: dict,
        content: str,
        approval_reason: str,
    ) -> str:
        """
        Move a task to Pending_Approval folder.

        Args:
            task_id: Task identifier
            metadata: Task metadata
            content: Task content
            approval_reason: Why approval is needed

        Returns:
            Path to approval file
        """
        # Add approval metadata
        metadata["status"] = "pending_approval"
        metadata["approval_status"] = "pending"
        metadata["approval_requested"] = datetime.now(timezone.utc).isoformat()

        approval_content = f"""---

# Awaiting Approval: {task_id}

**Reason:** {approval_reason}
**Requested:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Task Content
{content}

## Action Required
> [!APPROVAL] Review and set `approval_status: approved` or `approval_status: rejected`
"""

        task_path = self.create_task_file(
            task_id=task_id,
            metadata=metadata,
            content=approval_content,
            destination="pending_approval",
        )

        audit_log(
            action="task_sent_for_approval",
            task_id=task_id,
            details={"reason": approval_reason},
        )

        logger.info(f"Task {task_id} sent for approval: {approval_reason}")
        return task_path

    # ─── Audit Helpers ─────────────────────────────────────────────────

    def log_event(self, action: str, task_id: Optional[str] = None, details: dict | None = None):
        """Log a watcher event to audit trail."""
        audit_log(
            action=f"{self.name}_{action}",
            task_id=task_id,
            details=details or {},
        )

    def prune_state(self, state: dict, key: str, max_items: int = 500):
        """Prune a list in state to prevent bloat."""
        if key in state and len(state[key]) > max_items:
            state[key] = state[key][-max_items:]
