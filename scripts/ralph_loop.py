"""
Ralph Loop — Persistent Task Completion System (Ralph Wiggum Loop)
Named after the character who "keeps trying."

This system ensures tasks are NEVER abandoned. If a task fails,
it is re-injected into the processing loop with increased context
until it succeeds or hits max retries.

Flow:
1. Task enters Needs_Action
2. Orchestrator picks it up → processes
3. If FAIL → increment retry counter, add error context, re-inject
4. Loop until SUCCESS or MAX_RETRIES → then escalate to human
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger

# State tracking
RETRY_STATE_FILE = FOLDERS["logs"] / "ralph_loop_state.json"


def load_retry_state() -> dict:
    """Load retry state for all tasks."""
    if RETRY_STATE_FILE.exists():
        with open(RETRY_STATE_FILE, "r") as f:
            return json.load(f)
    return {"tasks": {}, "last_cleanup": None}


def save_retry_state(state: dict):
    """Save retry state."""
    with open(RETRY_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_task_retries(task_id: str) -> int:
    """Get current retry count for a task."""
    state = load_retry_state()
    return state["tasks"].get(task_id, {}).get("retries", 0)


def increment_retry(task_id: str, error_context: dict):
    """Increment retry counter and append error context."""
    state = load_retry_state()

    if task_id not in state["tasks"]:
        state["tasks"][task_id] = {
            "retries": 0,
            "errors": [],
            "first_attempt": datetime.now(timezone.utc).isoformat(),
        }

    state["tasks"][task_id]["retries"] += 1
    state["tasks"][task_id]["errors"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": error_context,
    })

    save_retry_state(state)
    return state["tasks"][task_id]["retries"]


def reinject_task(task: dict, result: dict):
    """
    Re-inject a failed task back into the processing pipeline.
    This is called by the orchestrator when a task execution fails.

    Args:
        task: The original task dict
        result: The execution result with error info
    """
    task_id = task.get("task_id", "unknown")
    max_retries = config.ralph_loop_max_retries
    tl = task_logger(task_id)

    # Track retry
    retry_count = increment_retry(task_id, result)
    tl.warning(f"Ralph Loop: Task {task_id} failed — retry #{retry_count}/{max_retries}")

    if retry_count >= max_retries:
        # Max retries hit — escalate to human
        tl.error(f"Ralph Loop: Task {task_id} exceeded max retries ({max_retries}) — ESCALATING TO HUMAN")
        _escalate_to_human(task, result)
        return

    # Re-inject into Needs_Action with enhanced context
    _reinject_to_needs_action(task, result, retry_count)

    # Trigger immediate re-processing
    tl.info(f"Ralph Loop: Re-injecting task {task_id} for immediate re-processing")
    audit_log(
        action="ralph_loop_reinjection",
        task_id=task_id,
        details={
            "retry": retry_count,
            "max_retries": max_retries,
            "error": result.get("error", "Unknown"),
        },
    )


def _reinject_to_needs_action(task: dict, result: dict, retry_count: int):
    """Write task back to Needs_Action with failure context."""
    task_id = task.get("task_id", "unknown")
    task_file = FOLDERS["needs_action"] / f"{task_id}.md"

    # Build enhanced content with error history
    error_history = ""
    for err in result.get("error_history", []):
        error_history += f"\n- Attempt {err['attempt']}: {err.get('error', 'Unknown')}"

    content = f"""---
task_id: {task_id}
source: {task.get('source', 'ralph_loop')}
created: {task.get('created', datetime.now(timezone.utc).isoformat())}
status: needs_action
priority: {task.get('priority', 'high')}
retry_count: {retry_count}
max_retries: {config.ralph_loop_max_retries}
---

# Task: {task_id} — RE-INJECTION #{retry_count}

> [!WARNING] This task has failed {retry_count} time(s). It will be re-processed automatically.

**Source:** {task.get('source', 'unknown')}
**Original Created:** {task.get('created', 'Unknown')}
**Retry Count:** {retry_count}/{config.ralph_loop_max_retries}

## Original Content
{task.get('_content', 'N/A')}

## Last Error
{result.get('error', 'Unknown error')}

## Error History
{error_history or "No detailed history available"}

## Action Required
> [!TODO] Re-process this task. The orchestrator will pick it up automatically.

## Ralph Loop Note
This task is under Ralph Wiggum Loop protection — it WILL NOT be abandoned.
"""
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Ralph Loop: Task {task_id} re-injected to Needs_Action (retry #{retry_count})")


def _escalate_to_human(task: dict, result: dict):
    """Escalate a task to human after max retries exceeded."""
    task_id = task.get("task_id", "unknown")
    escalation_file = FOLDERS["needs_action"] / f"{task_id}_ESCALATED.md"
    state = load_retry_state()
    task_state = state["tasks"].get(task_id, {})

    content = f"""---
task_id: {task_id}
source: {task.get('source', 'ralph_loop')}
created: {task.get('created', datetime.now(timezone.utc).isoformat())}
status: needs_action
priority: critical
escalated: true
escalation_time: {datetime.now(timezone.utc).isoformat()}
total_retries: {task_state.get('retries', 0)}
---

# 🚨 ESCALATED: {task_id} — HUMAN INTERVENTION REQUIRED

> [!CRITICAL] This task has FAILED {task_state.get('retries', 0)} times and could not be completed automatically.
> **Immediate human attention required.**

**Source:** {task.get('source', 'unknown')}
**First Attempt:** {task_state.get('first_attempt', 'Unknown')}
**Escalation Time:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Total Retries:** {task_state.get('retries', 0)}

## Original Content
{task.get('_content', 'N/A')}

## All Errors
"""
    for i, err in enumerate(task_state.get("errors", []), 1):
        content += f"\n{i}. [{err['timestamp']}] {json.dumps(err.get('context', {}), indent=2)}"

    content += f"""

## Action Required
> [!URGENT] Please review and handle this task manually.
> After resolution, move this file to the Done folder.

## Ralph Loop Status
> [!STOPPED] Ralph Loop has given up on this task after {config.ralph_loop_max_retries} attempts.
"""
    with open(escalation_file, "w", encoding="utf-8") as f:
        f.write(content)

    audit_log(
        action="ralph_loop_escalation",
        task_id=task_id,
        level="CRITICAL",
        details={"total_retries": task_state.get("retries", 0)},
    )
    logger.critical(f"Ralph Loop: Task {task_id} ESCALATED to human after {task_state.get('retries', 0)} failures")


def run_ralph_loop(poll_interval: int = 15):
    """
    Run Ralph Loop as a standalone process.
    Continuously monitors Needs_Action for tasks and triggers re-processing.
    """
    ensure_folders()
    logger.info(f"Ralph Loop started — monitoring every {poll_interval}s")
    audit_log(action="ralph_loop_started", details={"poll_interval": poll_interval})

    while True:
        try:
            # Check for tasks in Needs_Action that need re-processing
            needs_action_files = list(FOLDERS["needs_action"].glob("*.md"))

            if needs_action_files:
                logger.info(f"Ralph Loop: Found {len(needs_action_files)} task(s) in Needs_Action")

                for task_file in needs_action_files:
                    if "ESCALATED" in task_file.name:
                        continue  # Skip escalated tasks

                    # Read task to check retry count
                    content = task_file.read_text(encoding="utf-8")
                    if "---" in content:
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import yaml
                            try:
                                metadata = yaml.safe_load(parts[1])
                                retry_count = metadata.get("retry_count", 0)
                                task_id = metadata.get("task_id", "unknown")

                                if retry_count > 0:
                                    logger.info(f"Ralph Loop: Task {task_id} has {retry_count} retry(ies) — signaling orchestrator")
                                    audit_log(
                                        action="ralph_loop_monitoring",
                                        task_id=task_id,
                                        details={"retry_count": retry_count},
                                    )
                            except Exception as e:
                                logger.debug(f"Ralph Loop: Could not parse {task_file.name}: {e}")

            # Cleanup old state
            _cleanup_old_entries()

        except Exception as e:
            logger.error(f"Ralph Loop error: {e}")

        time.sleep(poll_interval)


def _cleanup_old_entries():
    """Remove old entries from retry state to prevent bloat."""
    state = load_retry_state()
    now = datetime.now(timezone.utc)

    to_remove = []
    for task_id, task_state in state["tasks"].items():
        first_attempt = datetime.fromisoformat(task_state.get("first_attempt", now.isoformat()))
        if (now - first_attempt).days > 7:  # Clean up after 7 days
            to_remove.append(task_id)

    for task_id in to_remove:
        del state["tasks"][task_id]

    if to_remove:
        state["last_cleanup"] = now.isoformat()
        save_retry_state(state)
        logger.debug(f"Ralph Loop: Cleaned up {len(to_remove)} old retry entries")


if __name__ == "__main__":
    run_ralph_loop()
