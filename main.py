"""
Personal AI Employee (Digital FTE) — Main Entry Point
Starts all subsystems: orchestrator, watchers, Ralph loop, scheduler, dashboard, watchdog.

Usage:
    python main.py start          # Start full system
    python main.py start --daemon  # Start in background
    python main.py status          # Show system status
    python main.py stop            # Stop all processes
    python main.py dashboard       # Update dashboard once
    python main.py approve <id>    # Approve a task
    python main.py reject <id>     # Reject a task
    python main.py test            # Run system diagnostics
"""

import sys
import signal
import argparse
import threading
import time
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import config, ensure_folders, validate_config, FOLDERS, LOGS_DIR
from logger_setup import logger, audit_log, setup_logger


class AISystem:
    """Main system controller — starts and coordinates all subsystems."""

    def __init__(self):
        ensure_folders()
        self._running = False
        self._threads: dict[str, threading.Thread] = {}

    def start(self):
        """Start the entire AI Employee system."""
        self._running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("=" * 70)
        logger.info("  🤖 PERSONAL AI EMPLOYEE — Digital FTE v1.0")
        logger.info("  Hackathon Project: Bronze → Silver Upgrade")
        logger.info("=" * 70)

        # Startup validation
        warnings = validate_config()
        if warnings:
            logger.warning(f"Configuration warnings ({len(warnings)}):")
            for w in warnings:
                logger.warning(f"  ⚠️  {w}")

        # Log system info
        logger.info(f"Project Root: {PROJECT_ROOT}")
        logger.info(f"Log Level: {config.log_level}")
        logger.info(f"AI Model: {'Claude' if config.anthropic_api_key else 'OpenAI' if config.openai_api_key else 'None configured'}")

        # Write startup log
        audit_log(
            action="system_startup",
            details={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "python": sys.version,
                "platform": sys.platform,
            },
        )

        # Start subsystems in order
        self._start_dashboard()
        self._start_scheduler()
        self._start_ralph_loop()
        self._start_watchdog_monitor()
        self._start_orchestrator()

        logger.info("=" * 70)
        logger.info("  ✅ ALL SYSTEMS ONLINE — AI Employee is operational")
        logger.info("=" * 70)
        audit_log(action="system_online")

        # Print quick start info
        print("\n" + "=" * 70)
        print("  🤖 Personal AI Employee — ONLINE")
        print("=" * 70)
        print(f"  Dashboard: {PROJECT_ROOT / 'DASHBOARD.md'}")
        print(f"  Inbox:     {FOLDERS['inbox']}")
        print(f"  Logs:      {LOGS_DIR}")
        print(f"  Approvals: {FOLDERS['pending_approval']}")
        print("-" * 70)
        print("  Commands:")
        print("    Approve task: python main.py approve <task_id>")
        print("    Reject task:  python main.py reject <task_id>")
        print("    Status:       python main.py status")
        print("    Stop:         Press Ctrl+C")
        print("=" * 70 + "\n")

        # Keep main thread alive
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Gracefully stop all subsystems."""
        if not self._running:
            return

        self._running = False
        logger.info("System shutdown initiated...")
        audit_log(action="system_shutdown")

        # Stop all threads
        for name, thread in self._threads.items():
            logger.info(f"Stopping: {name}")
            # Threads are daemon so they'll die with main process

        logger.info("All systems stopped. Goodbye! 👋")

    def _signal_handler(self, signum, frame):
        """Handle OS signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)

    # ─── Subsystem Starters ────────────────────────────────────────────

    def _start_dashboard(self):
        """Start dashboard generator in background thread."""
        from scripts.dashboard_generator import DashboardGenerator

        dg = DashboardGenerator()
        t = threading.Thread(target=dg.start, daemon=True, name="dashboard")
        t.start()
        self._threads["dashboard"] = t

        # Initial dashboard update
        dg.generate()
        logger.info("Dashboard generator started")

    def _start_scheduler(self):
        """Start task scheduler in background thread."""
        from scripts.scheduler import TaskScheduler

        scheduler = TaskScheduler()
        scheduler.start()
        logger.info("Task scheduler started")

    def _start_ralph_loop(self):
        """Start Ralph Loop in background thread."""
        from scripts.ralph_loop import run_ralph_loop

        t = threading.Thread(
            target=lambda: run_ralph_loop(poll_interval=15),
            daemon=True,
            name="ralph_loop",
        )
        t.start()
        self._threads["ralph_loop"] = t
        logger.info("Ralph Loop started")

    def _start_watchdog_monitor(self):
        """
        Start watchdog in background thread.
        Note: Watchdog spawns actual subprocesses for each component.
        """
        from scripts.watchdog import Watchdog, PROCESSES

        # Disable orchestrator in watchdog since we start it directly
        PROCESSES["orchestrator"]["enabled"] = False

        wd = Watchdog()
        wd.start_all()

        t = threading.Thread(target=wd.monitor_loop, daemon=True, name="watchdog")
        t.start()
        self._threads["watchdog"] = t
        logger.info("Watchdog process manager started")

    def _start_orchestrator(self):
        """Start main orchestrator in background thread."""
        from orchestrator import Orchestrator

        orch = Orchestrator()

        def _orch_loop():
            orch._running = True
            orch._startup_checks()
            orch._start_watchers()
            orch._main_loop()

        t = threading.Thread(target=_orch_loop, daemon=True, name="orchestrator")
        t.start()
        self._threads["orchestrator"] = t
        logger.info("Orchestrator main loop started")


# ─── CLI Commands ──────────────────────────────────────────────────────

def cmd_start():
    """Start the full system."""
    system = AISystem()
    system.start()


def cmd_status():
    """Show current system status."""
    from config import PIDS_DIR
    import psutil

    ensure_folders()

    print("\n🤖 Personal AI Employee — Status")
    print("=" * 50)

    # Check process PID files
    processes = [
        "orchestrator", "gmail_watcher", "whatsapp_watcher",
        "finance_watcher", "filesystem_watcher", "ralph_loop",
        "watchdog", "gmail_mcp", "whatsapp_mcp", "linkedin_mcp",
    ]

    for name in processes:
        pid_file = PIDS_DIR / f"{name}.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                running = psutil.pid_exists(pid)
                status = "✅ Running" if running else "❌ Dead (stale PID)"
                print(f"  {name:25s} {status} (PID: {pid})")
            except ValueError:
                print(f"  {name:25s} ❌ Invalid PID file")
        else:
            print(f"  {name:25s} ⚪ Not started")

    # Show vault stats
    print("\n📊 Vault Stats:")
    from config import FOLDERS
    for name, folder in FOLDERS.items():
        if folder.exists():
            count = len(list(folder.glob("*.md")))
            print(f"  {name:25s} {count} file(s)")

    print()


def cmd_stop():
    """Stop all processes."""
    from config import PIDS_DIR
    import psutil

    print("Stopping all AI Employee processes...")

    for pid_file in sorted(PIDS_DIR.glob("*.pid")):
        try:
            pid = int(pid_file.read_text().strip())
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                    print(f"  Stopped: {pid_file.stem} (PID: {pid})")
                except psutil.TimeoutExpired:
                    proc.kill()
                    print(f"  Killed: {pid_file.stem} (PID: {pid})")
            else:
                print(f"  Already dead: {pid_file.stem}")
            pid_file.unlink()
        except (ValueError, Exception) as e:
            print(f"  Error with {pid_file.stem}: {e}")

    print("All processes stopped.")


def cmd_approve(task_id: str):
    """Approve a pending task."""
    from scripts.approval_system import ApprovalSystem

    approval = ApprovalSystem()
    success = approval.approve_task(task_id)
    print(f"{'✅ Approved' if success else '❌ Failed'}: {task_id}")


def cmd_reject(task_id: str, reason: str = ""):
    """Reject a pending task."""
    from scripts.approval_system import ApprovalSystem

    approval = ApprovalSystem()
    success = approval.reject_task(task_id, reason=reason or "Rejected via CLI")
    print(f"{'✅ Rejected' if success else '❌ Failed'}: {task_id}")


def cmd_dashboard_once():
    """Update dashboard once."""
    from scripts.dashboard_generator import DashboardGenerator

    dg = DashboardGenerator()
    dg.generate()
    print(f"Dashboard updated: {PROJECT_ROOT / 'DASHBOARD.md'}")


def cmd_test():
    """Run system diagnostics."""
    import importlib

    print("\n🔍 Personal AI Employee — System Diagnostics")
    print("=" * 50)

    # Check Python version
    print(f"\n  Python: {sys.version}")
    print(f"  Platform: {sys.platform}")

    # Check critical modules
    modules = [
        "dotenv", "yaml", "pydantic",
        "fastapi", "uvicorn",
        "playwright",
        "googleapiclient",
        "watchdog",
        "schedule",
        "tenacity",
        "psutil",
    ]

    print("\n  Module Check:")
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"    ✅ {mod}")
        except ImportError:
            print(f"    ❌ {mod} (not installed)")

    # Check folder structure
    ensure_folders()
    print("\n  Folder Check:")
    from config import FOLDERS
    for name, folder in FOLDERS.items():
        exists = folder.exists()
        print(f"    {'✅' if exists else '❌'} {name}: {folder}")

    # Check config
    print("\n  Configuration:")
    warnings = validate_config()
    if warnings:
        for w in warnings:
            print(f"    ⚠️  {w}")
    else:
        print("    ✅ No configuration warnings")

    # Check .env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print(f"\n  ✅ .env file exists")
    else:
        print(f"\n  ⚠️  .env file not found (copy .env.example to .env)")

    print("\n" + "=" * 50)
    print("Diagnostics complete.\n")


def cmd_list_pending():
    """List pending approval tasks."""
    from scripts.approval_system import ApprovalSystem

    approval = ApprovalSystem()
    pending = approval.list_pending()

    if pending:
        print("\n⏳ Pending Approvals:")
        print("-" * 50)
        for p in pending:
            print(f"  ID:     {p['task_id']}")
            print(f"  Source: {p['source']}")
            print(f"  Reason: {p['reason']}")
            print(f"  File:   {p['file']}")
            print("-" * 50)
    else:
        print("\n✅ No pending approvals")


# ─── Gold-Level Commands ───────────────────────────────────────────────

def cmd_ceo_briefing():
    """Generate CEO briefing on demand."""
    from scripts.ceo_briefing import generate_ceo_briefing

    print("\n📊 Generating CEO Briefing...")
    path = generate_ceo_briefing()
    print(f"✅ Briefing generated: {path}")


def cmd_demo(dry_run: bool = False):
    """Run end-to-end demo pipeline."""
    from scripts.demo_pipeline import DemoPipeline

    pipeline = DemoPipeline(dry_run=dry_run)
    pipeline.run()


def cmd_generate_linkedin_post(topic: str, tone: str = "professional", length: str = "medium"):
    """Generate a LinkedIn post and save as draft."""
    import asyncio
    from mcp_servers.linkedin_mcp.server import handle_generate_post

    print(f"\n📝 Generating LinkedIn post about: {topic}")
    result = asyncio.run(handle_generate_post(topic=topic, tone=tone, length=length))
    print(result[0].text)


def cmd_finance_summary():
    """Generate monthly finance summary."""
    from scripts.finance_watcher import generate_monthly_summary

    print("\n💸 Generating Monthly Finance Summary...")
    path = generate_monthly_summary()
    print(f"✅ Summary generated: {path}")


def cmd_subscriptions():
    """Run subscription detection scan."""
    from scripts.finance_watcher import detect_subscriptions_in_history

    print("\n🔍 Scanning for subscriptions...")
    subs = detect_subscriptions_in_history()
    if subs:
        print(f"Found {len(subs)} subscription(s):\n")
        for s in subs:
            print(f"  {s['vendor']}: ${s['amount']}/mo ({s['frequency']})")
    else:
        print("No subscriptions detected.")


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Personal AI Employee — Digital FTE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Silver Commands:
  python main.py start              Start full system
  python main.py status             Show system status
  python main.py stop               Stop all processes
  python main.py approve TASK_ID    Approve a task
  python main.py reject TASK_ID     Reject a task
  python main.py dashboard          Update dashboard once
  python main.py test               Run diagnostics
  python main.py list-pending       List pending approvals

Gold Commands:
  python main.py ceo-briefing       Generate CEO weekly briefing
  python main.py demo               Run end-to-end demo pipeline
  python main.py demo --dry-run     Preview demo without creating files
  python main.py linkedin-post "AI trends"  Generate LinkedIn post draft
  python main.py finance-summary    Generate monthly finance summary
  python main.py subscriptions      Scan for recurring subscriptions
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("start", help="Start full system")
    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("stop", help="Stop all processes")
    subparsers.add_parser("dashboard", help="Update dashboard once")
    subparsers.add_parser("test", help="Run system diagnostics")
    subparsers.add_parser("list-pending", help="List pending approvals")

    approve_parser = subparsers.add_parser("approve", help="Approve a task")
    approve_parser.add_argument("task_id", help="Task ID to approve")

    reject_parser = subparsers.add_parser("reject", help="Reject a task")
    reject_parser.add_argument("task_id", help="Task ID to reject")
    reject_parser.add_argument("--reason", default="", help="Rejection reason")

    # Gold-level commands
    subparsers.add_parser("ceo-briefing", help="Generate CEO weekly briefing")

    demo_parser = subparsers.add_parser("demo", help="Run end-to-end demo pipeline")
    demo_parser.add_argument("--dry-run", action="store_true", help="Preview without creating files")

    linkedin_parser = subparsers.add_parser("linkedin-post", help="Generate LinkedIn post draft")
    linkedin_parser.add_argument("topic", help="Post topic")
    linkedin_parser.add_argument("--tone", default="professional", help="Tone: professional, casual, thought_leader, promotional")
    linkedin_parser.add_argument("--length", default="medium", help="Length: short, medium, long")

    subparsers.add_parser("finance-summary", help="Generate monthly finance summary")
    subparsers.add_parser("subscriptions", help="Scan for recurring subscriptions")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "status":
        cmd_status()
    elif args.command == "stop":
        cmd_stop()
    elif args.command == "approve":
        cmd_approve(args.task_id)
    elif args.command == "reject":
        cmd_reject(args.task_id, args.reason)
    elif args.command == "dashboard":
        cmd_dashboard_once()
    elif args.command == "test":
        cmd_test()
    elif args.command == "list-pending":
        cmd_list_pending()
    # Gold-level commands
    elif args.command == "ceo-briefing":
        cmd_ceo_briefing()
    elif args.command == "demo":
        cmd_demo(dry_run=args.dry_run)
    elif args.command == "linkedin-post":
        cmd_generate_linkedin_post(args.topic, tone=args.tone, length=args.length)
    elif args.command == "finance-summary":
        cmd_finance_summary()
    elif args.command == "subscriptions":
        cmd_subscriptions()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
