"""
Dashboard Generator — Creates Obsidian-compatible dashboard.md
Real-time system status, task counts, recent activity, and quick actions.
Updates every 30 seconds and writes to project root for Obsidian to display.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import config, FOLDERS, PROJECT_ROOT, ensure_folders
from logger_setup import logger, audit_log

DASHBOARD_FILE = PROJECT_ROOT / "DASHBOARD.md"
UPDATE_INTERVAL = 30  # seconds


class DashboardGenerator:
    """Generates and maintains the Obsidian dashboard markdown file."""

    def __init__(self):
        ensure_folders()
        self._running = False

    def start(self):
        """Start dashboard auto-update loop."""
        self._running = True
        logger.info(f"Dashboard generator started — updating every {UPDATE_INTERVAL}s")

        while self._running:
            try:
                self.generate()
            except Exception as e:
                logger.error(f"Dashboard generation error: {e}")
            time.sleep(UPDATE_INTERVAL)

    def stop(self):
        """Stop dashboard updates."""
        self._running = False
        logger.info("Dashboard generator stopped")

    def generate(self):
        """Generate the full dashboard markdown file."""
        now = datetime.now(timezone.utc)

        # Gather metrics
        metrics = {
            "inbox": self._count_files(FOLDERS["inbox"]),
            "needs_action": self._count_files(FOLDERS["needs_action"]),
            "plans": self._count_files(FOLDERS["plans"]),
            "pending_approval": self._count_files(FOLDERS["pending_approval"]),
            "approved": self._count_files(FOLDERS["approved"]),
            "rejected": self._count_files(FOLDERS["rejected"]),
            "done": self._count_files(FOLDERS["done"]),
            "review_required": self._count_files(FOLDERS["review_required"]),
        }

        total_tasks = sum(metrics.values())
        completed = metrics["done"]
        pending = metrics["inbox"] + metrics["needs_action"] + metrics["pending_approval"]

        # Recent activity from audit log
        recent_activity = self._get_recent_activity(10)

        # System status
        system_status = self._get_system_status()

        # Build markdown
        content = f"""---
type: dashboard
updated: {now.isoformat()}
version: 1.0.0
---

# 🤖 Personal AI Employee — Dashboard

> **Last Updated:** {now.strftime("%Y-%m-%d %H:%M:%S UTC")}
> **Status:** {"🟢 Online" if system_status["healthy"] else "🔴 Issues Detected"}

---

## 📊 Task Overview

| Status | Count | Folder |
|--------|-------|--------|
| 📥 Inbox | {metrics['inbox']} | `Inbox/` |
| ⚡ Needs Action | {metrics['needs_action']} | `Needs_Action/` |
| 📋 Plans | {metrics['plans']} | `Plans/` |
| ⏳ Pending Approval | {metrics['pending_approval']} | `Pending_Approval/` |
| ✅ Approved | {metrics['approved']} | `Approved/` |
| ❌ Rejected | {metrics['rejected']} | `Rejected/` |
| 🏁 Done | {metrics['done']} | `Done/` |
| 👀 Review Required | {metrics['review_required']} | `Review_Required/` |
| **Total** | **{total_tasks}** | |

### Completion Rate
"""
        if total_tasks > 0:
            rate = (completed / total_tasks) * 100
            content += f"- **Completed:** {completed}/{total_tasks} ({rate:.1f}%)\n"
            content += f"- **Pending:** {pending}\n"
        else:
            content += "- No tasks yet — system is idle and waiting for work.\n"

        content += f"""
---

## 🖥️ System Status

| Component | Status |
|-----------|--------|
| Orchestrator | {"🟢 Running" if system_status.get('orchestrator') else "🔴 Stopped"} |
| Gmail Watcher | {"🟢 Running" if system_status.get('gmail_watcher') else "🔴 Stopped"} |
| WhatsApp Watcher | {"🟢 Running" if system_status.get('whatsapp_watcher') else "🔴 Stopped"} |
| Finance Watcher | {"🟢 Running" if system_status.get('finance_watcher') else "🔴 Stopped"} |
| Filesystem Watcher | {"🟢 Running" if system_status.get('filesystem_watcher') else "🔴 Stopped"} |
| Ralph Loop | {"🟢 Running" if system_status.get('ralph_loop') else "🔴 Stopped"} |
| Watchdog | {"🟢 Running" if system_status.get('watchdog') else "🔴 Stopped"} |

---

## 🕐 Recent Activity (Last 10)

"""
        if recent_activity:
            for entry in recent_activity:
                ts = entry.get("timestamp", "")[:19]
                action = entry.get("action", "Unknown")
                task_id = entry.get("task_id", "")
                content += f"- `{ts}` — **{action}**"
                if task_id:
                    content += f" ({task_id})"
                content += "\n"
        else:
            content += "- No recent activity recorded.\n"

        content += f"""
---

## ⚡ Quick Actions

- [[Pending_Approval/|Review Pending Approvals]] — {metrics['pending_approval']} item(s) awaiting approval
- [[Needs_Action/|Handle Tasks Needing Action]] — {metrics['needs_action']} item(s)
- [[Inbox/|Process Inbox]] — {metrics['inbox']} item(s)
- [[Logs/audit.jsonl|View Full Audit Log]]
- [[Logs/system.log|View System Log]]

---

## 📝 Ralph Loop Status

"""
        ralph_state_file = FOLDERS["logs"] / "ralph_loop_state.json"
        if ralph_state_file.exists():
            with open(ralph_state_file, "r") as f:
                ralph_state = json.load(f)
            active_retries = len(ralph_state.get("tasks", {}))
            content += f"- **Active Retry Tasks:** {active_retries}\n"
            if active_retries > 0:
                content += "- Tasks under Ralph Loop protection will be automatically re-tried.\n"
        else:
            content += "- Ralph Loop state not yet initialized.\n"

        content += f"""
---

> 🔄 *This dashboard auto-updates every {UPDATE_INTERVAL} seconds.*
> Open in Obsidian for the best viewing experience.
"""
        # Write to file
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Dashboard updated — {total_tasks} total tasks")

    # ─── Helpers ───────────────────────────────────────────────────────

    def _count_files(self, folder: Path) -> int:
        """Count .md files in a folder."""
        if not folder.exists():
            return 0
        return len(list(folder.glob("*.md")))

    def _get_recent_activity(self, limit: int = 10) -> list[dict]:
        """Get recent entries from audit log."""
        audit_log_file = FOLDERS["logs"] / "audit.jsonl"
        if not audit_log_file.exists():
            return []

        entries = []
        try:
            with open(audit_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            return []

        return entries[-limit:]

    def _get_system_status(self) -> dict:
        """Get status of system components via PID files."""
        status = {"healthy": True}

        for name in ["orchestrator", "gmail_watcher", "whatsapp_watcher", "finance_watcher", "filesystem_watcher", "ralph_loop", "watchdog"]:
            pid_file = Path(__file__).resolve().parent.parent / ".pids" / f"{name}.pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    import psutil
                    status[name] = psutil.pid_exists(pid)
                except (ValueError, Exception):
                    status[name] = False
            else:
                status[name] = False

            if not status[name]:
                status["healthy"] = False

        return status


# ─── Module-level convenience ─────────────────────────────────────────

_dashboard = None


def get_dashboard_generator() -> DashboardGenerator:
    """Singleton accessor."""
    global _dashboard
    if _dashboard is None:
        _dashboard = DashboardGenerator()
    return _dashboard


def update_dashboard():
    """One-shot dashboard update."""
    get_dashboard_generator().generate()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Single update
        DashboardGenerator().generate()
        print("Dashboard updated")
    else:
        # Continuous mode
        dg = DashboardGenerator()
        try:
            dg.start()
        except KeyboardInterrupt:
            dg.stop()
