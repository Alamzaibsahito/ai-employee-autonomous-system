"""
Watchdog — Auto-Restart Process Manager
Monitors all AI Employee subsystems and automatically restarts any that crash.
Uses PID files for tracking and psutil for process monitoring.
"""

import os
import sys
import time
import signal
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import psutil

from config import config, PIDS_DIR, SCRIPTS_DIR, ensure_folders
from logger_setup import logger, audit_log

# Process definitions: name -> (script/module, args, restart_delay)
PROCESSES = {
    "gmail_watcher": {
        "script": str(SCRIPTS_DIR / "gmail_watcher.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": True,
    },
    "filesystem_watcher": {
        "script": str(SCRIPTS_DIR / "filesystem_watcher.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": True,
    },
    "finance_watcher": {
        "script": str(SCRIPTS_DIR / "finance_watcher.py"),
        "args": [],
        "restart_delay": 15,
        "enabled": True,
    },
    "whatsapp_watcher": {
        "script": str(SCRIPTS_DIR / "whatsapp_watcher.py"),
        "args": [],
        "restart_delay": 15,
        "enabled": True,
    },
    "ralph_loop": {
        "script": str(SCRIPTS_DIR / "ralph_loop.py"),
        "args": [],
        "restart_delay": 5,
        "enabled": True,
    },
    "orchestrator": {
        "script": str(Path(__file__).resolve().parent / "orchestrator.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": True,
    },
    "gmail_mcp": {
        "script": str(Path(__file__).resolve().parent / "mcp_servers" / "gmail_mcp" / "server.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": False,  # Only enable if Gmail credentials configured
    },
    "whatsapp_mcp": {
        "script": str(Path(__file__).resolve().parent / "mcp_servers" / "whatsapp_mcp" / "server.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": True,
    },
    "linkedin_mcp": {
        "script": str(Path(__file__).resolve().parent / "mcp_servers" / "linkedin_mcp" / "server.py"),
        "args": [],
        "restart_delay": 10,
        "enabled": True,
    },
}


class Watchdog:
    """Monitors and auto-restarts all AI Employee processes."""

    def __init__(self):
        ensure_folders()
        self._processes: dict[str, subprocess.Popen] = {}
        self._last_restart: dict[str, float] = {}
        self._running = False

    def start_all(self):
        """Start all configured processes."""
        self._running = True
        logger.info("=" * 60)
        logger.info("WATCHDOG STARTED — Auto-Restart Process Manager")
        logger.info("=" * 60)
        audit_log(action="watchdog_started")

        for name, proc_config in PROCESSES.items():
            if not proc_config.get("enabled", True):
                logger.info(f"Watchdog: Skipping disabled process: {name}")
                continue

            self._start_process(name, proc_config)

    def stop_all(self):
        """Gracefully stop all managed processes."""
        self._running = False
        logger.info("Watchdog: Stopping all processes...")

        for name, proc in self._processes.items():
            try:
                if proc.poll() is None:  # Still running
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    logger.info(f"Watchdog: Stopped {name}")
            except Exception as e:
                logger.error(f"Watchdog: Error stopping {name}: {e}")

        # Clean up PID files
        for pid_file in PIDS_DIR.glob("*.pid"):
            pid_file.unlink(missing_ok=True)

        audit_log(action="watchdog_stopped")

    def monitor_loop(self):
        """Main monitoring loop — check and restart processes."""
        logger.info("Watchdog: Monitoring loop started — checking every 5 seconds")

        while self._running:
            try:
                for name, proc_config in PROCESSES.items():
                    if not proc_config.get("enabled", True):
                        continue

                    self._check_process(name, proc_config)

                time.sleep(5)

            except KeyboardInterrupt:
                logger.info("Watchdog: Monitoring loop interrupted")
                self.stop_all()
                break
            except Exception as e:
                logger.error(f"Watchdog: Monitoring loop error: {e}")
                time.sleep(10)

    def _start_process(self, name: str, proc_config: dict) -> Optional[subprocess.Popen]:
        """Start a single process and track its PID."""
        script = proc_config["script"]
        args = proc_config.get("args", [])

        if not Path(script).exists():
            logger.warning(f"Watchdog: Script not found, skipping {name}: {script}")
            return None

        # Check restart cooldown
        last_restart = self._last_restart.get(name, 0)
        cooldown = proc_config.get("restart_delay", 10)
        if time.time() - last_restart < cooldown:
            remaining = cooldown - (time.time() - last_restart)
            logger.debug(f"Watchdog: {name} in cooldown — restarting in {remaining:.0f}s")
            return None

        logger.info(f"Watchdog: Starting {name}...")

        try:
            cmd = [sys.executable, script] + args
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )

            # Write PID file
            pid_file = PIDS_DIR / f"{name}.pid"
            with open(pid_file, "w") as f:
                f.write(str(proc.pid))

            self._processes[name] = proc
            self._last_restart[name] = time.time()

            logger.info(f"Watchdog: {name} started with PID {proc.pid}")
            audit_log(action="process_started", details={"name": name, "pid": proc.pid})

            return proc

        except Exception as e:
            logger.error(f"Watchdog: Failed to start {name}: {e}")
            audit_log(action="process_start_failed", level="ERROR", details={"name": name, "error": str(e)})
            return None

    def _check_process(self, name: str, proc_config: dict):
        """Check if a process is still running, restart if not."""
        proc = self._processes.get(name)

        if proc is None:
            # Not tracked yet — start it
            self._start_process(name, proc_config)
            return

        # Check if process is still running
        if proc.poll() is not None:
            # Process has exited
            exit_code = proc.returncode
            logger.warning(f"Watchdog: {name} exited with code {exit_code}")
            audit_log(
                action="process_exited",
                level="WARNING" if exit_code != 0 else "INFO",
                details={"name": name, "exit_code": exit_code},
            )

            # Read stderr for error info
            try:
                stderr_output = proc.stderr.read().decode("utf-8", errors="replace")[-500:]
                if stderr_output:
                    logger.error(f"Watchdog: {name} stderr: {stderr_output}")
            except Exception:
                pass

            # Clean up
            del self._processes[name]
            pid_file = PIDS_DIR / f"{name}.pid"
            pid_file.unlink(missing_ok=True)

            # Restart
            logger.info(f"Watchdog: Restarting {name}...")
            self._start_process(name, proc_config)

    def get_status(self) -> dict:
        """Get status of all managed processes."""
        status = {}

        for name, proc_config in PROCESSES.items():
            proc = self._processes.get(name)
            is_running = proc is not None and proc.poll() is None

            status[name] = {
                "running": is_running,
                "enabled": proc_config.get("enabled", True),
                "pid": proc.pid if proc else None,
                "last_restart": self._last_restart.get(name),
                "exit_code": proc.returncode if proc else None,
            }

        return status

    def restart_process(self, name: str) -> bool:
        """Manually restart a specific process."""
        if name not in PROCESSES:
            logger.warning(f"Watchdog: Unknown process: {name}")
            return False

        # Kill existing
        proc = self._processes.get(name)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

        if proc:
            del self._processes[name]

        # Force restart by resetting cooldown
        self._last_restart[name] = 0
        result = self._start_process(name, PROCESSES[name])
        return result is not None


# ─── CLI Interface ─────────────────────────────────────────────────────

def main():
    """CLI for watchdog."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Employee Watchdog Process Manager")
    parser.add_argument("command", choices=["start", "stop", "status", "restart"], help="Command to run")
    parser.add_argument("process", nargs="?", help="Process name (for restart command)")
    args = parser.parse_args()

    watchdog = Watchdog()

    if args.command == "start":
        logger.info("Watchdog: Starting all processes...")
        watchdog.start_all()
        watchdog.monitor_loop()

    elif args.command == "stop":
        watchdog.stop_all()
        logger.info("Watchdog: All processes stopped")

    elif args.command == "status":
        status = watchdog.get_status()
        print("\nProcess Status:")
        print("-" * 60)
        for name, info in status.items():
            status_icon = "✅" if info["running"] else "❌"
            enabled_str = "" if info["enabled"] else " (disabled)"
            pid_str = f"PID: {info['pid']}" if info["pid"] else "Not running"
            print(f"  {status_icon} {name}{enabled_str} — {pid_str}")
        print()

    elif args.command == "restart":
        if not args.process:
            print("Usage: python watchdog.py restart <process_name>")
            sys.exit(1)
        success = watchdog.restart_process(args.process)
        print(f"{'✅ Restarted' if success else '❌ Failed'}: {args.process}")


if __name__ == "__main__":
    main()
