"""
Scheduler — Cron/Loop Scheduling System
Manages periodic tasks using the `schedule` library.
Handles: dashboard updates, approval expiry checks, log rotation, system health checks.
"""

import time
import threading
from datetime import datetime, timezone

import schedule

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log


class TaskScheduler:
    """Manages all periodic/scheduled tasks for the AI Employee system."""

    def __init__(self):
        ensure_folders()
        self._running = False
        self._thread: threading.Thread | None = None

    def configure_schedule(self):
        """Set up all scheduled tasks."""

        # Dashboard update every 30 seconds
        schedule.every(30).seconds.do(self._run_dashboard_update)

        # Check expired approvals every 5 minutes
        schedule.every(5).minutes.do(self._run_approval_check)

        # System health check every 2 minutes
        schedule.every(2).minutes.do(self._run_health_check)

        # Log summary every hour
        schedule.every(1).hours.do(self._run_log_summary)

        # Daily cleanup at midnight
        schedule.every().day.at("00:00").do(self._run_daily_cleanup)

        # Gmail check every 60 seconds (if not running as standalone watcher)
        schedule.every(60).seconds.do(self._run_gmail_check)

        # ─── Gold-Level Scheduled Tasks ────────────────────────────────

        # CEO Briefing every Sunday at configured hour
        briefing_day = config.ceo_briefing_day.lower()
        briefing_hour = config.ceo_briefing_hour
        schedule.every().sunday.at(f"{briefing_hour:02d}:00").do(self._run_ceo_briefing)

        # Finance monthly summary on the 1st of each month
        schedule.every().day.at("09:00").do(self._run_finance_monthly_check)

        # LinkedIn scheduled post check every 15 minutes
        schedule.every(15).minutes.do(self._run_linkedin_schedule_check)

        # Subscription detection scan weekly (Sunday morning)
        schedule.every().sunday.at("08:00").do(self._run_subscription_scan)

        logger.info(f"Scheduler: All tasks configured (CEO briefing: Sunday {briefing_hour}:00)")

    def start(self):
        """Start the scheduler in a background thread."""
        self._running = True
        self.configure_schedule()

        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("Scheduler started (background thread)")
        audit_log(action="scheduler_started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        schedule.clear()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Scheduler stopped")

    def _scheduler_loop(self):
        """Internal scheduler event loop."""
        logger.info("Scheduler event loop running")

        while self._running:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(1)

    # ─── Scheduled Tasks ───────────────────────────────────────────────

    def _run_dashboard_update(self):
        """Update the Obsidian dashboard."""
        try:
            from scripts.dashboard_generator import update_dashboard
            update_dashboard()
            logger.debug("Scheduled: Dashboard updated")
        except Exception as e:
            logger.error(f"Scheduled dashboard update failed: {e}")

    def _run_approval_check(self):
        """Check for expired approval requests."""
        try:
            from scripts.approval_system import ApprovalSystem
            approval = ApprovalSystem()
            expired = approval.check_expired_approvals()
            for task_id in expired:
                approval.handle_expired(task_id)
            if expired:
                logger.info(f"Scheduled: {len(expired)} expired approval(s) handled")
        except Exception as e:
            logger.error(f"Scheduled approval check failed: {e}")

    def _run_health_check(self):
        """Run system health check."""
        try:
            from scripts.watchdog import Watchdog
            watchdog = Watchdog()
            status = watchdog.get_status()

            unhealthy = [name for name, info in status.items() if info["enabled"] and not info["running"]]
            if unhealthy:
                logger.warning(f"Scheduled health check: Unhealthy processes: {', '.join(unhealthy)}")
                audit_log(
                    action="health_check_warning",
                    level="WARNING",
                    details={"unhealthy": unhealthy},
                )
        except Exception as e:
            logger.error(f"Scheduled health check failed: {e}")

    def _run_log_summary(self):
        """Generate hourly log summary."""
        try:
            from logger_setup import AUDIT_LOG

            if not AUDIT_LOG.exists():
                return

            # Count recent entries
            one_hour_ago = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            count = 0

            with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    if '"timestamp"' in line:
                        count += 1

            logger.info(f"Scheduled: Hourly log summary — {count} audit entries in log file")

        except Exception as e:
            logger.error(f"Scheduled log summary failed: {e}")

    def _run_daily_cleanup(self):
        """Daily maintenance tasks."""
        try:
            logger.info("Scheduled: Running daily cleanup")

            # Clean up old Ralph loop state
            from scripts.ralph_loop import _cleanup_old_entries
            _cleanup_old_entries()

            # Clean up old PID files
            from config import PIDS_DIR
            import psutil

            for pid_file in PIDS_DIR.glob("*.pid"):
                try:
                    pid = int(pid_file.read_text().strip())
                    if not psutil.pid_exists(pid):
                        pid_file.unlink()
                        logger.debug(f"Cleaned up stale PID file: {pid_file.name}")
                except (ValueError, Exception):
                    pid_file.unlink(missing_ok=True)

            audit_log(action="daily_cleanup_completed")
            logger.info("Scheduled: Daily cleanup complete")

        except Exception as e:
            logger.error(f"Scheduled daily cleanup failed: {e}")

    def _run_gmail_check(self):
        """Periodic Gmail check."""
        try:
            from scripts.gmail_watcher import check_gmail
            check_gmail()
        except Exception as e:
            logger.error(f"Scheduled Gmail check failed: {e}")

    # ─── Gold-Level Scheduled Tasks ────────────────────────────────────

    def _run_ceo_briefing(self):
        """Generate weekly CEO briefing."""
        try:
            from scripts.ceo_briefing import generate_ceo_briefing
            path = generate_ceo_briefing()
            logger.info(f"Scheduled: CEO Briefing generated — {path}")
            audit_log(action="ceo_briefing_scheduled", details={"file": path})
        except Exception as e:
            logger.error(f"Scheduled CEO briefing failed: {e}")

    def _run_finance_monthly_check(self):
        """Generate monthly finance summary if it's the 1st of the month."""
        try:
            from scripts.finance_watcher import generate_monthly_summary
            now = datetime.now(timezone.utc)
            if now.day == 1:
                path = generate_monthly_summary()
                logger.info(f"Scheduled: Monthly finance summary generated — {path}")
                audit_log(action="finance_monthly_summary", details={"file": path})
        except Exception as e:
            logger.error(f"Scheduled finance monthly check failed: {e}")

    def _run_linkedin_schedule_check(self):
        """Check for LinkedIn posts scheduled for now and publish them."""
        try:
            from config import FOLDERS
            drafts_folder = FOLDERS["drafts"]
            if not drafts_folder.exists():
                return

            now = datetime.now(timezone.utc)

            for draft_file in drafts_folder.glob("*.md"):
                content = draft_file.read_text(encoding="utf-8")

                # Check if scheduled and approved
                if "scheduled_for:" not in content:
                    continue
                if "approved: true" not in content.lower():
                    continue
                if "status: published" in content.lower():
                    continue

                # Extract scheduled time
                import re
                match = re.search(r"scheduled_for:\s*(.+)", content)
                if match:
                    try:
                        scheduled_time = datetime.fromisoformat(match.group(1).strip())
                        if scheduled_time <= now:
                            # Time to publish
                            import yaml
                            meta = yaml.safe_load(content.split("---")[1])
                            post_id = meta.get("post_id", draft_file.stem)
                            logger.info(f"Scheduled: LinkedIn post {post_id} is due — publishing")

                            # In production, call the MCP publish tool here
                            audit_log(
                                action="linkedin_scheduled_post_due",
                                task_id=post_id,
                                details={"scheduled_for": str(scheduled_time)},
                            )
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            logger.error(f"Scheduled LinkedIn check failed: {e}")

    def _run_subscription_scan(self):
        """Run subscription detection scan."""
        try:
            from scripts.finance_watcher import detect_subscriptions_in_history
            subscriptions = detect_subscriptions_in_history()
            if subscriptions:
                logger.info(
                    f"Scheduled: Subscription scan found {len(subscriptions)} subscriptions"
                )
                audit_log(
                    action="subscription_scan",
                    details={"count": len(subscriptions), "vendors": [s["vendor"] for s in subscriptions]},
                )
        except Exception as e:
            logger.error(f"Scheduled subscription scan failed: {e}")

    def run_once(self, task_name: str):
        """Run a specific scheduled task immediately."""
        task_map = {
            "dashboard": self._run_dashboard_update,
            "approval-check": self._run_approval_check,
            "health-check": self._run_health_check,
            "log-summary": self._run_log_summary,
            "daily-cleanup": self._run_daily_cleanup,
            "gmail-check": self._run_gmail_check,
            # Gold-level tasks
            "ceo-briefing": self._run_ceo_briefing,
            "finance-monthly": self._run_finance_monthly_check,
            "linkedin-schedule": self._run_linkedin_schedule_check,
            "subscription-scan": self._run_subscription_scan,
        }

        task = task_map.get(task_name)
        if task:
            task()
            logger.info(f"Ran scheduled task: {task_name}")
        else:
            logger.warning(f"Unknown scheduled task: {task_name}")


# ─── Module-level convenience ─────────────────────────────────────────

_scheduler = None


def get_scheduler() -> TaskScheduler:
    """Singleton accessor."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


if __name__ == "__main__":
    import sys

    scheduler = TaskScheduler()

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        if len(sys.argv) > 2:
            scheduler.run_once(sys.argv[2])
        else:
            print("Usage: python scheduler.py once <task-name>")
            print("Available: dashboard, approval-check, health-check, log-summary, daily-cleanup, gmail-check")
            print("Gold-level: ceo-briefing, finance-monthly, linkedin-schedule, subscription-scan")
    else:
        scheduler.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
