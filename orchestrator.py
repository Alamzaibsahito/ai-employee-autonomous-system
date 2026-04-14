"""
Orchestrator — Main Brain Loop for Personal AI Employee
Coordinates all subsystems: watchers, MCP servers, approval system, Ralph loop, scheduler.
Implements the Claude reasoning cycle: Read → Plan → Write → Execute.
"""

import time
import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger
from scripts.gmail_watcher import check_gmail
from scripts.filesystem_watcher import FileChangeHandler
from scripts.finance_watcher import check_finances
from scripts.whatsapp_watcher import check_whatsapp_messages


class SystemState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class Orchestrator:
    """Main controller for the Personal AI Employee system."""

    def __init__(self):
        ensure_folders()
        self.state = SystemState.IDLE
        self._running = False
        self._threads: dict[str, threading.Thread] = {}
        self._ralph_loop = None
        self._scheduler = None
        self.current_task: Optional[dict] = None
        self.cycle_count = 0

    # ─── Lifecycle ─────────────────────────────────────────────────────

    def start(self):
        """Start the orchestrator and all subsystems."""
        self._running = True
        self.state = SystemState.IDLE
        logger.info("=" * 60)
        logger.info("ORCHESTRATOR STARTING — Personal AI Employee v1.0")
        logger.info("=" * 60)
        audit_log(action="orchestrator_started")

        # Run startup checks
        self._startup_checks()

        # Start watchers in background threads
        self._start_watchers()

        # Start main processing loop
        logger.info("Starting main processing loop...")
        self._main_loop()

    def stop(self):
        """Gracefully shut down the orchestrator."""
        self.state = SystemState.SHUTTING_DOWN
        self._running = False
        logger.info("Orchestrator: Shutting down...")
        audit_log(action="orchestrator_stopping")

    # ─── Startup ───────────────────────────────────────────────────────

    def _startup_checks(self):
        """Validate system configuration before starting."""
        from config import validate_config

        warnings = validate_config()
        for warning in warnings:
            logger.warning(f"CONFIG: {warning}")

        # Check vault folders
        for name, path in FOLDERS.items():
            if path.exists():
                logger.debug(f"Vault folder OK: {name} -> {path}")
            else:
                logger.warning(f"Vault folder missing, creating: {name}")
                path.mkdir(parents=True, exist_ok=True)

        logger.info("Startup checks complete")

    def _start_watchers(self):
        """Start watcher threads."""

        def _gmail_loop():
            logger.info("Gmail Watcher thread started")
            while self._running:
                try:
                    check_gmail()
                except Exception as e:
                    logger.error(f"Gmail watcher thread error: {e}")
                time.sleep(60)

        def _finance_loop():
            logger.info("Finance Watcher thread started")
            while self._running:
                try:
                    check_finances()
                except Exception as e:
                    logger.error(f"Finance watcher thread error: {e}")
                time.sleep(300)

        def _whatsapp_loop():
            logger.info("WhatsApp Watcher thread started")
            while self._running:
                try:
                    check_whatsapp_messages()
                except Exception as e:
                    logger.error(f"WhatsApp watcher thread error: {e}")
                time.sleep(10)

        # Start watcher threads (daemon so they die with main process)
        for name, target, interval in [
            ("gmail", _gmail_loop, 60),
            ("finance", _finance_loop, 300),
            ("whatsapp", _whatsapp_loop, 10),
        ]:
            t = threading.Thread(target=target, daemon=True, name=f"watcher-{name}")
            t.start()
            self._threads[name] = t
            logger.info(f"Started watcher thread: {name}")

    # ─── Main Loop ─────────────────────────────────────────────────────

    def _main_loop(self):
        """
        Main orchestrator loop.
        Continuously scans Inbox for tasks, processes them through the reasoning cycle.
        """
        logger.info("Main loop running — scanning for tasks every 10 seconds")

        while self._running:
            try:
                self.cycle_count += 1
                logger.debug(f"Main loop cycle #{self.cycle_count}")

                # Scan for pending tasks
                tasks = self._scan_inbox()

                for task in tasks:
                    self.current_task = task
                    self.state = SystemState.PROCESSING
                    self._process_task(task)
                    self.current_task = None

                # Scan for tasks awaiting approval
                approved_tasks = self._check_approvals()
                for task in approved_tasks:
                    self._execute_task(task)

                self.state = SystemState.IDLE
                time.sleep(10)

            except KeyboardInterrupt:
                logger.info("Main loop interrupted by user")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.state = SystemState.ERROR
                audit_log(action="main_loop_error", level="ERROR", details={"error": str(e)})
                time.sleep(30)

    # ─── Task Scanning ─────────────────────────────────────────────────

    def _scan_inbox(self) -> list[dict]:
        """Scan Inbox/Needs_Action for tasks ready to process."""
        tasks = []
        for folder_name in ["inbox", "needs_action"]:
            folder = FOLDERS[folder_name]
            if not folder.exists():
                continue

            for task_file in folder.glob("*.md"):
                task = self._parse_task_file(task_file)
                if task:
                    tasks.append(task)
                    logger.info(f"Found task: {task['task_id']} in {folder_name}")

        return tasks

    def _parse_task_file(self, path: Path) -> Optional[dict]:
        """Parse a markdown task file and return dict with metadata."""
        try:
            content = path.read_text(encoding="utf-8")

            # Extract YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    metadata = yaml.safe_load(parts[1])
                    metadata["_path"] = str(path)
                    metadata["_content"] = parts[2].strip()
                    return metadata
        except Exception as e:
            logger.error(f"Failed to parse task file {path}: {e}")

        return None

    def _check_approvals(self) -> list[dict]:
        """Check Pending_Approval for tasks that have been approved."""
        approved = []
        approval_folder = FOLDERS["pending_approval"]
        if not approval_folder.exists():
            return approved

        for task_file in approval_folder.glob("*.md"):
            task = self._parse_task_file(task_file)
            if task and task.get("approval_status") == "approved":
                approved.append(task)
                logger.info(f"Task approved: {task['task_id']}")

        return approved

    # ─── Claude Reasoning Cycle: Read → Plan → Write → Execute ─────────

    def _process_task(self, task: dict):
        """Process a single task through the full reasoning cycle."""
        task_id = task.get("task_id", "unknown")
        tl = task_logger(task_id)
        tl.info(f"Processing task: {task_id}")
        audit_log(action="task_processing_started", task_id=task_id)

        try:
            # Step 1: READ — Understand the task
            tl.info("Step 1/4: READ — Analyzing task")
            analysis = self._read_task(task)
            tl.info(f"Analysis: {analysis}")

            # Step 2: PLAN — Generate action plan
            tl.info("Step 2/4: PLAN — Generating plan")
            plan = self._plan_task(task, analysis)
            if not plan:
                tl.warning("Could not generate plan — moving to Needs_Action")
                self._move_task(task, "needs_action")
                return

            # Step 3: WRITE — Save plan and check if approval needed
            tl.info("Step 3/4: WRITE — Saving plan")
            plan_path = self._save_plan(task, plan)
            tl.info(f"Plan saved to {plan_path}")

            # Check if this task requires human approval
            if self._requires_approval(task, plan):
                tl.info("Task requires human approval — moving to Pending_Approval")
                self._move_task_to_approval(task, plan)
                return

            # Step 4: EXECUTE — Run the plan
            tl.info("Step 4/4: EXECUTE — Executing plan")
            result = self._execute_task(task)

            if result.get("success"):
                tl.info(f"Task completed successfully: {task_id}")
                self._move_task(task, "done")
                audit_log(action="task_completed", task_id=task_id, details={"result": result})
            else:
                tl.warning(f"Task execution failed: {result.get('error', 'Unknown error')}")
                # Re-inject into Ralph loop
                self._reinject_ralph_loop(task, result)

        except Exception as e:
            tl.error(f"Task processing error: {e}")
            audit_log(action="task_processing_error", task_id=task_id, level="ERROR", details={"error": str(e)})
            self._move_task(task, "needs_action")

    def _read_task(self, task: dict) -> str:
        """
        READ step: Analyze task content and determine what needs to be done.
        In production, this would call Claude/OpenAI for NLP analysis.
        """
        source = task.get("source", "unknown")
        content = task.get("_content", "")
        subject = task.get("subject", "")

        # Simple heuristic analysis
        analysis_parts = []
        if source == "gmail_watcher":
            analysis_parts.append(f"Email task: {subject}")
            if "urgent" in content.lower() or "asap" in content.lower():
                analysis_parts.append("HIGH PRIORITY — urgent language detected")
        elif source == "filesystem_watcher":
            analysis_parts.append(f"File event: {task.get('event_type', 'unknown')}")
        elif source == "whatsapp_watcher":
            analysis_parts.append(f"WhatsApp message from {task.get('contact', 'unknown')}")
        elif source == "finance_watcher":
            analysis_parts.append(f"Finance alert: ${task.get('amount', 0)}")

        # AI reasoning (if API key available)
        ai_analysis = self._call_ai_reasoning(
            f"Analyze this task and suggest actions: {content[:500]}"
        )
        if ai_analysis:
            analysis_parts.append(f"AI: {ai_analysis}")

        return " | ".join(analysis_parts)

    def _plan_task(self, task: dict, analysis: str) -> Optional[dict]:
        """
        PLAN step: Generate a structured action plan for the task.
        Returns list of steps or None if plan cannot be generated.
        """
        source = task.get("source", "")
        plan_steps = []

        if source == "gmail_watcher":
            plan_steps = [
                {"action": "read_email", "details": {"email_id": task.get("email_id", "")}},
                {"action": "analyze_content", "details": {"subject": task.get("subject", "")}},
                {"action": "draft_response", "details": {}},
                {"action": "await_approval", "details": {"reason": "Email response requires review"}},
            ]
        elif source == "whatsapp_watcher":
            plan_steps = [
                {"action": "read_full_message", "details": {"contact": task.get("contact", "")}},
                {"action": "generate_response", "details": {}},
                {"action": "await_approval", "details": {"reason": "WhatsApp response requires review"}},
            ]
        elif source == "finance_watcher":
            plan_steps = [
                {"action": "review_transaction", "details": {"amount": task.get("amount", 0)}},
                {"action": "categorize", "details": {}},
                {"action": "notify_user", "details": {}},
            ]
        else:
            plan_steps = [
                {"action": "review", "details": {"task": task.get("task_id", "")}},
                {"action": "determine_action", "details": {}},
            ]

        return {"steps": plan_steps, "analysis": analysis}

    def _save_plan(self, task: dict, plan: dict) -> str:
        """Save plan to Plans folder."""
        task_id = task.get("task_id", "unknown")
        plan_file = FOLDERS["plans"] / f"{task_id}_plan.md"

        content = f"""---
task_id: {task_id}
created: {datetime.now(timezone.utc).isoformat()}
status: planned
---

# Plan for {task_id}

## Analysis
{plan.get('analysis', 'N/A')}

## Steps
"""
        for i, step in enumerate(plan.get("steps", []), 1):
            content += f"\n{i}. **{step['action']}** — {step.get('details', {})}"

        content += "\n\n## Execution Log\n"

        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(content)

        return str(plan_file)

    def _execute_task(self, task: dict) -> dict:
        """
        EXECUTE step: Run the planned actions through MCP layer.
        Returns {"success": bool, "error": str|None, "details": dict}
        """
        task_id = task.get("task_id", "")
        tl = task_logger(task_id)
        source = task.get("source", "")

        tl.info(f"Executing task from source: {source}")

        try:
            if source == "gmail_watcher":
                # Mark email as read via MCP
                email_id = task.get("email_id", "")
                if email_id:
                    tl.info(f"Marking email {email_id} as read")
                    # In production, call MCP tool here
                    audit_log(
                        action="email_marked_read",
                        task_id=task_id,
                        details={"email_id": email_id},
                    )
                return {"success": True, "details": {"action": "email_processed"}}

            elif source == "whatsapp_watcher":
                tl.info("WhatsApp message acknowledged")
                return {"success": True, "details": {"action": "message_acknowledged"}}

            elif source == "finance_watcher":
                tl.info(f"Finance alert processed: ${task.get('amount', 0)}")
                return {"success": True, "details": {"action": "alert_processed"}}

            else:
                tl.info("Generic task processed")
                return {"success": True, "details": {"action": "generic_processed"}}

        except Exception as e:
            tl.error(f"Execution error: {e}")
            return {"success": False, "error": str(e)}

    def _requires_approval(self, task: dict, plan: dict) -> bool:
        """Determine if a task requires human approval before execution."""
        source = task.get("source", "")
        content = task.get("_content", "").lower()

        # Finance tasks always need approval
        if source == "finance_watcher":
            return True

        # Messaging to new contacts needs approval
        if source in ["gmail_watcher", "whatsapp_watcher"]:
            approval_keywords = ["send", "reply", "respond", "contact", "new"]
            for kw in approval_keywords:
                if kw in content:
                    return True

        # Payment-related actions
        if any(kw in content for kw in ["pay", "payment", "transfer", "approve money"]):
            return True

        return False

    def _move_task_to_approval(self, task: dict, plan: dict):
        """Move task to Pending_Approval folder."""
        task_id = task.get("task_id", "unknown")
        old_path = task.get("_path", "")
        approval_file = FOLDERS["pending_approval"] / f"{task_id}.md"

        content = f"""---
task_id: {task_id}
source: {task.get('source', 'unknown')}
created: {task.get('created', datetime.now(timezone.utc).isoformat())}
status: pending_approval
approval_status: pending
approval_requested: {datetime.now(timezone.utc).isoformat()}
---

# Awaiting Approval: {task_id}

**Source:** {task.get('source', 'unknown')}
**Requested:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Task Content
{task.get('_content', 'N/A')}

## Proposed Plan
{json.dumps(plan.get('steps', []), indent=2)}

## Action Required
> [!APPROVAL] Review the proposed plan and approve or reject.
> Set `approval_status: approved` or `approval_status: rejected` in the frontmatter.
"""
        with open(approval_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Remove from source folder
        if old_path:
            Path(old_path).unlink(missing_ok=True)

        audit_log(action="task_sent_for_approval", task_id=task_id)
        logger.info(f"Task {task_id} sent for approval")

    def _reinject_ralph_loop(self, task: dict, result: dict):
        """Re-inject failed task into Ralph loop for retry."""
        from scripts.ralph_loop import reinject_task

        task_id = task.get("task_id", "unknown")
        logger.info(f"Re-injecting task {task_id} into Ralph loop (attempt)")

        try:
            reinject_task(task, result)
        except Exception as e:
            logger.error(f"Ralph re-injection failed for {task_id}: {e}")
            self._move_task(task, "needs_action")

    def _move_task(self, task: dict, destination: str):
        """Move task file to destination folder."""
        task_id = task.get("task_id", "unknown")
        old_path = task.get("_path", "")
        if not old_path:
            return

        dest_folder = FOLDERS.get(destination)
        if not dest_folder:
            logger.warning(f"Unknown destination folder: {destination}")
            return

        new_path = dest_folder / Path(old_path).name

        # Update status in file
        try:
            content = Path(old_path).read_text(encoding="utf-8")
            content = content.replace(
                f"status: {task.get('status', 'inbox')}",
                f"status: {destination}"
            )
            content = content.replace(
                f"completed: {datetime.now(timezone.utc).isoformat()}",
                f"completed: {datetime.now(timezone.utc).isoformat()}"
            )
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)
            Path(old_path).unlink(missing_ok=True)
            logger.info(f"Task {task_id} moved to {destination}")
        except Exception as e:
            logger.error(f"Failed to move task {task_id}: {e}")

    # ─── AI Reasoning ──────────────────────────────────────────────────

    def _call_ai_reasoning(self, prompt: str) -> Optional[str]:
        """Call AI API for reasoning (Claude or OpenAI fallback)."""
        if config.anthropic_api_key:
            return self._call_claude(prompt)
        elif config.openai_api_key:
            return self._call_openai(prompt)
        else:
            logger.debug("No AI API key configured — skipping AI reasoning")
            return None

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Anthropic Claude API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system="You are an AI Employee assistant. Provide concise, actionable analysis.",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else None
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API (fallback)."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI Employee assistant. Be concise."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
            )
            return response.choices[0].message.content if response.choices else None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None


# ─── Module-level convenience ─────────────────────────────────────────

def create_orchestrator() -> Orchestrator:
    """Factory function for orchestrator."""
    return Orchestrator()


if __name__ == "__main__":
    orch = create_orchestrator()
    try:
        orch.start()
    except KeyboardInterrupt:
        orch.stop()
        logger.info("Orchestrator stopped")
