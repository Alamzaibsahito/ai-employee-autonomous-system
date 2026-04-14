"""
Approval System — Human-in-the-Loop (HITL) Workflow
Manages task approval flow: Pending_Approval → Approved/Rejected
Supports CLI approval, API endpoints, and file-based approval.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger

# Approval rules configuration
APPROVAL_RULES = {
    # Always require approval for these actions
    "always_require": [
        "send_message_to_new_contact",
        "payment",
        "transfer",
        "delete_email",
        "post_update",
        "send_connection_request",
    ],
    # Auto-approve below these thresholds
    "auto_approve_thresholds": {
        "finance_amount": 100.00,  # Auto-approve transactions below $100
    },
    # Trusted contacts (no approval needed)
    "trusted_contacts": [],  # Add contact names here
}


class ApprovalSystem:
    """Manages human-in-the-loop approval workflow."""

    def __init__(self):
        ensure_folders()

    def submit_for_approval(self, task: dict, plan: dict, reason: str = "") -> str:
        """
        Submit a task for human approval.
        Creates approval request file in Pending_Approval folder.

        Returns: path to approval file
        """
        task_id = task.get("task_id", "unknown")
        approval_file = FOLDERS["pending_approval"] / f"{task_id}.md"

        # Build approval markdown
        content = f"""---
task_id: {task_id}
source: {task.get('source', 'unknown')}
created: {task.get('created', datetime.now(timezone.utc).isoformat())}
status: pending_approval
approval_status: pending
approval_requested: {datetime.now(timezone.utc).isoformat()}
approval_reason: {reason}
priority: {task.get('priority', 'normal')}
---

# ⏳ Approval Required: {task_id}

**Submitted:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Source:** {task.get('source', 'unknown')}
**Reason:** {reason or "Action requires human review"}

## Task Summary
{task.get('_content', 'N/A')[:500]}

## Proposed Actions
{self._format_plan_steps(plan)}

## How to Approve
> [!APPROVAL] Choose one of the following:
>
> 1. **Approve:** Change `approval_status: pending` → `approval_status: approved`
> 2. **Reject:** Change `approval_status: pending` → `approval_status: rejected`
> 3. **Modify:** Edit the plan steps above and then approve
>
> You can also run: `python scripts/approval_system.py approve {task_id}`
> Or: `python scripts/approval_system.py reject {task_id}`

## Timeout
> [!WARNING] This request will auto-expire after {config.approval_timeout_seconds / 3600:.0f} hours.
"""
        with open(approval_file, "w", encoding="utf-8") as f:
            f.write(content)

        audit_log(
            action="approval_submitted",
            task_id=task_id,
            details={"reason": reason, "file": str(approval_file)},
        )
        logger.info(f"Approval submitted for task {task_id}: {reason}")

        return str(approval_file)

    def approve_task(self, task_id: str, approver: str = "human") -> bool:
        """
        Approve a pending task.
        Moves file from Pending_Approval → Approved.
        """
        pending_file = FOLDERS["pending_approval"] / f"{task_id}.md"
        if not pending_file.exists():
            logger.warning(f"Approval: Task {task_id} not found in Pending_Approval")
            return False

        try:
            # Read and update content
            content = pending_file.read_text(encoding="utf-8")
            content = content.replace("approval_status: pending", "approval_status: approved")
            content = content.replace("status: pending_approval", "status: approved")
            content = content.replace(
                f"priority: {self._extract_priority(content)}",
                f"priority: {self._extract_priority(content)}"
            )
            # Add approval metadata
            content = content.replace(
                "---\n# ⏳ Approval Required:",
                f"---\n# ✅ Approved: {task_id}\n\n**Approved by:** {approver}\n**Approved at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

            # Move to Approved folder
            approved_file = FOLDERS["approved"] / f"{task_id}.md"
            with open(approved_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Remove from pending
            pending_file.unlink()

            audit_log(
                action="task_approved",
                task_id=task_id,
                user=approver,
                details={"approved_file": str(approved_file)},
            )
            logger.info(f"Task {task_id} approved by {approver}")
            return True

        except Exception as e:
            logger.error(f"Approval error for {task_id}: {e}")
            return False

    def reject_task(self, task_id: str, reason: str = "", rejector: str = "human") -> bool:
        """
        Reject a pending task.
        Moves file from Pending_Approval → Rejected.
        """
        pending_file = FOLDERS["pending_approval"] / f"{task_id}.md"
        if not pending_file.exists():
            logger.warning(f"Approval: Task {task_id} not found in Pending_Approval")
            return False

        try:
            content = pending_file.read_text(encoding="utf-8")
            content = content.replace("approval_status: pending", f"approval_status: rejected")
            content = content.replace("status: pending_approval", "status: rejected")

            # Add rejection metadata
            content += f"\n\n## Rejected\n**Rejected by:** {rejector}\n**Reason:** {reason or 'No reason provided'}\n**Time:** {datetime.now(timezone.utc).isoformat()}"

            # Move to Rejected folder
            rejected_file = FOLDERS["rejected"] / f"{task_id}.md"
            with open(rejected_file, "w", encoding="utf-8") as f:
                f.write(content)

            pending_file.unlink()

            audit_log(
                action="task_rejected",
                task_id=task_id,
                user=rejector,
                details={"reason": reason},
            )
            logger.info(f"Task {task_id} rejected by {rejector}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Rejection error for {task_id}: {e}")
            return False

    def check_expired_approvals(self) -> list[str]:
        """
        Check for approval requests that have exceeded timeout.
        Returns list of expired task IDs.
        """
        expired = []
        approval_folder = FOLDERS["pending_approval"]
        if not approval_folder.exists():
            return expired

        now = datetime.now(timezone.utc)

        for approval_file in approval_folder.glob("*.md"):
            content = approval_file.read_text(encoding="utf-8")
            if "approval_requested:" in content:
                import re
                match = re.search(r"approval_requested:\s*(.+)", content)
                if match:
                    try:
                        requested_at = datetime.fromisoformat(match.group(1).strip())
                        elapsed = (now - requested_at).total_seconds()
                        if elapsed > config.approval_timeout_seconds:
                            expired.append(approval_file.stem)
                            logger.warning(f"Approval expired for task {approval_file.stem} ({elapsed:.0f}s old)")
                    except ValueError:
                        pass

        return expired

    def handle_expired(self, task_id: str):
        """Handle an expired approval request — move back to Needs_Action."""
        pending_file = FOLDERS["pending_approval"] / f"{task_id}.md"
        if not pending_file.exists():
            return

        content = pending_file.read_text(encoding="utf-8")
        content = content.replace("approval_status: pending", "approval_status: expired")
        content = content.replace("status: pending_approval", "status: needs_action")
        content += f"\n\n## Expired\n> [!EXPIRED] Approval request expired. Re-submit if still needed.\n**Expired at:** {datetime.now(timezone.utc).isoformat()}"

        needs_action_file = FOLDERS["needs_action"] / f"{task_id}.md"
        with open(needs_action_file, "w", encoding="utf-8") as f:
            f.write(content)

        pending_file.unlink()

        audit_log(
            action="approval_expired",
            task_id=task_id,
            level="WARNING",
        )
        logger.warning(f"Approval for task {task_id} expired — moved to Needs_Action")

    def should_require_approval(self, task: dict, action: str = "") -> bool:
        """
        Determine if an action requires approval based on rules.
        """
        # Check always-required list
        if action in APPROVAL_RULES["always_require"]:
            return True

        # Check task content for approval triggers
        content = f"{task.get('_content', '')} {task.get('source', '')}".lower()

        # Payment-related
        if any(kw in content for kw in ["pay", "payment", "transfer", "money", "bank"]):
            return True

        # New contact messaging
        if any(kw in content for kw in ["new contact", "send_message_to_new_contact"]):
            return True

        # Posting to social
        if any(kw in content for kw in ["post", "publish", "share"]):
            return True

        return False

    def list_pending(self) -> list[dict]:
        """List all pending approval requests."""
        pending = []
        approval_folder = FOLDERS["pending_approval"]
        if not approval_folder.exists():
            return pending

        for approval_file in approval_folder.glob("*.md"):
            content = approval_file.read_text(encoding="utf-8")
            import re
            task_id_match = re.search(r"task_id:\s*(\S+)", content)
            source_match = re.search(r"source:\s*(\S+)", content)
            reason_match = re.search(r"approval_reason:\s*(.*)", content)

            pending.append({
                "task_id": task_id_match.group(1) if task_id_match else approval_file.stem,
                "source": source_match.group(1) if source_match else "unknown",
                "reason": reason_match.group(1).strip() if reason_match else "No reason",
                "file": str(approval_file),
            })

        return pending

    # ─── Helpers ───────────────────────────────────────────────────────

    def _format_plan_steps(self, plan: dict) -> str:
        """Format plan steps as markdown."""
        if isinstance(plan, list):
            steps = plan
        elif isinstance(plan, dict):
            steps = plan.get("steps", [])
        else:
            return "No plan available"

        if not steps:
            return "No plan available"

        output = ""
        for i, step in enumerate(steps, 1):
            if isinstance(step, dict):
                action = step.get("action", "Unknown")
                details = step.get("details", step.get("params", ""))
                output += f"{i}. **{action}** — {details}\n"
            else:
                output += f"{i}. {step}\n"

        return output

    def _extract_priority(self, content: str) -> str:
        """Extract priority from YAML frontmatter."""
        import re
        match = re.search(r"priority:\s*(\S+)", content)
        return match.group(1) if match else "normal"


# ─── CLI Interface ─────────────────────────────────────────────────────

def main():
    """CLI for approval system."""
    import sys

    approval = ApprovalSystem()

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python approval_system.py approve <task_id>")
        print("  python approval_system.py reject <task_id> [reason]")
        print("  python approval_system.py list")
        print("  python approval_system.py check-expired")
        sys.exit(1)

    command = sys.argv[1].lower()
    task_id = sys.argv[2]

    if command == "approve":
        success = approval.approve_task(task_id)
        print(f"{'✅ Approved' if success else '❌ Failed'}: {task_id}")
    elif command == "reject":
        reason = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "No reason provided"
        success = approval.reject_task(task_id, reason=reason)
        print(f"{'✅ Rejected' if success else '❌ Failed'}: {task_id}")
    elif command == "list":
        pending = approval.list_pending()
        if pending:
            print("Pending approvals:")
            for p in pending:
                print(f"  - {p['task_id']} (source: {p['source']}, reason: {p['reason']})")
        else:
            print("No pending approvals")
    elif command == "check-expired":
        expired = approval.check_expired_approvals()
        for task_id in expired:
            approval.handle_expired(task_id)
            print(f"Handled expired approval: {task_id}")
        if not expired:
            print("No expired approvals")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
