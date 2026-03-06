"""
============================================================
Platinum Tier - Health Monitor
============================================================
Monitors all AI Employee services and auto-recovers on failure

Features:
- Monitors watchers, MCP servers, orchestrator
- Auto-restart on failure
- Logs errors to central log
- Writes alerts to Vault/Updates/

Usage:
    python health_monitor.py

Runs as a daemon - checks every 30 seconds
============================================================
"""

import os
import sys
import time
import logging
import subprocess
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
LOG_DIR = "Logs/central"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "health_monitor.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Service definitions
SERVICES = {
    "file_watcher": {
        "script": "file_watcher.py",
        "type": "python",
        "restart_delay": 2,
        "max_restarts": 5,
    },
    "process_tasks": {
        "script": "process_tasks.py",
        "type": "python",
        "restart_delay": 2,
        "max_restarts": 5,
    },
    "ralph_loop": {
        "script": "skills/ralph_loop.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 3,
    },
    "gmail_mcp": {
        "script": "mcp_servers/gmail_mcp/server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8001,
    },
    "linkedin_mcp": {
        "script": "mcp_servers/linkedin_mcp/server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8002,
    },
    "odoo_mcp": {
        "script": "mcp_servers/odoo_mcp/server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8003,
    },
    "twitter_mcp": {
        "script": "mcp_servers/social_mcp/twitter_server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8004,
    },
    "facebook_mcp": {
        "script": "mcp_servers/social_mcp/facebook_server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8005,
    },
    "instagram_mcp": {
        "script": "mcp_servers/social_mcp/instagram_server.py",
        "type": "python",
        "restart_delay": 3,
        "max_restarts": 5,
        "port": 8006,
    },
}

# PID directory
PID_DIR = ".pids"
os.makedirs(PID_DIR, exist_ok=True)

# Vault Updates folder for alerts
VAULT_UPDATES = "AI_Employee_Vault/Updates"
os.makedirs(VAULT_UPDATES, exist_ok=True)


class ServiceMonitor:
    """Monitor and manage service health."""
    
    def __init__(self):
        self.restart_counts: Dict[str, int] = {}
        self.last_check: Dict[str, datetime] = {}
        self.alerts: List[Dict] = []
        
    def check_process_by_name(self, name: str) -> bool:
        """Check if a process is running by name."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                    if name in cmdline and 'python' in cmdline:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            logger.error(f"Error checking process {name}: {e}")
            return False
    
    def check_process_by_pid(self, name: str) -> bool:
        """Check if a process is running by PID file."""
        pid_file = os.path.join(PID_DIR, f"{name}.pid")
        
        if not os.path.exists(pid_file):
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, FileNotFoundError):
            return False
    
    def check_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def is_service_healthy(self, name: str, config: Dict) -> Tuple[bool, str]:
        """
        Check if a service is healthy.
        
        Returns:
            Tuple of (is_healthy, reason)
        """
        # Check by PID file
        if self.check_process_by_pid(name):
            return True, "running"
        
        # Check by process name
        if self.check_process_by_name(name):
            return True, "running"
        
        # Check by port (for MCP servers)
        if "port" in config:
            if self.check_port_in_use(config["port"]):
                return True, "port_active"
        
        return False, "not_running"
    
    def restart_service(self, name: str, config: Dict) -> bool:
        """Restart a failed service."""
        try:
            script_path = config["script"]
            
            if not os.path.exists(script_path):
                logger.error(f"Script not found: {script_path}")
                self.write_alert(
                    name, 
                    "CRITICAL", 
                    f"Script not found: {script_path}"
                )
                return False
            
            # Check restart count
            current_count = self.restart_counts.get(name, 0)
            if current_count >= config["max_restarts"]:
                logger.error(f"Max restarts exceeded for {name}")
                self.write_alert(
                    name, 
                    "CRITICAL", 
                    f"Max restarts ({config['max_restarts']}) exceeded. Manual intervention required."
                )
                return False
            
            # Start the service
            logger.info(f"Restarting {name}...")
            
            cmd = [sys.executable, script_path]
            
            # Start as background process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Save PID
            pid_file = os.path.join(PID_DIR, f"{name}.pid")
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            self.restart_counts[name] = current_count + 1
            
            logger.info(f"Service {name} restarted (PID: {process.pid})")
            
            self.write_alert(
                name,
                "WARNING",
                f"Service restarted (attempt {current_count + 1}/{config['max_restarts']})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart {name}: {e}")
            self.write_alert(
                name,
                "ERROR",
                f"Restart failed: {str(e)}"
            )
            return False
    
    def write_alert(self, service: str, level: str, message: str) -> None:
        """Write alert to Vault/Updates/."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            alert_file = os.path.join(VAULT_UPDATES, f"alert_{service}_{timestamp}.md")
            
            alert_content = f"""---
Type: health_alert
Level: {level}
Service: {service}
Timestamp: {datetime.now().isoformat()}
---

# Health Alert: {service}

## Severity: {level}

**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Service:** `{service}`

## Issue

{message}

## Recommended Action

"""
            if level == "CRITICAL":
                alert_content += """
- **IMMEDIATE ACTION REQUIRED**
- Check service logs: `Logs/central/{service}.log`
- Verify configuration
- Consider manual restart
"""
            elif level == "ERROR":
                alert_content += """
- Check service logs for details
- Verify dependencies
- Review recent changes
"""
            elif level == "WARNING":
                alert_content += """
- Monitor service closely
- Check for recurring patterns
"""
            else:
                alert_content += "- Review and monitor"
            
            with open(alert_file, 'w', encoding='utf-8') as f:
                f.write(alert_content)
            
            logger.info(f"Alert written: {alert_file}")
            
        except Exception as e:
            logger.error(f"Failed to write alert: {e}")
    
    def check_all_services(self) -> Dict[str, Dict]:
        """Check health of all services."""
        results = {}
        
        for name, config in SERVICES.items():
            is_healthy, reason = self.is_service_healthy(name, config)
            
            results[name] = {
                "healthy": is_healthy,
                "reason": reason,
                "restarts": self.restart_counts.get(name, 0),
            }
            
            if not is_healthy:
                logger.warning(f"Service {name} is not healthy: {reason}")
                
                # Attempt restart
                if self.restart_service(name, config):
                    results[name]["restarting"] = True
                else:
                    results[name]["critical"] = True
            
            self.last_check[name] = datetime.now()
        
        return results
    
    def generate_health_report(self, results: Dict[str, Dict]) -> str:
        """Generate health report."""
        total = len(results)
        healthy = sum(1 for r in results.values() if r["healthy"])
        unhealthy = total - healthy
        
        report = f"""
============================================================
           AI Employee Health Report
           {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
============================================================

Summary:
  Total Services: {total}
  Healthy: {healthy}
  Unhealthy: {unhealthy}

Service Status:
"""
        
        for name, status in results.items():
            status_icon = "✓" if status["healthy"] else "✗"
            restarts = status.get("restarts", 0)
            restart_info = f" (restarts: {restarts})" if restarts > 0 else ""
            
            report += f"  [{status_icon}] {name}: {status['reason']}{restart_info}\n"
        
        report += "\n============================================================\n"
        
        return report


def run_monitor():
    """Run the health monitor daemon."""
    logger.info("Starting Health Monitor daemon...")
    logger.info(f"Monitoring {len(SERVICES)} services")
    logger.info(f"Check interval: 30 seconds")
    
    monitor = ServiceMonitor()
    check_interval = 30  # seconds
    report_interval = 300  # Generate report every 5 minutes
    
    last_report_time = time.time()
    
    try:
        while True:
            # Check all services
            results = monitor.check_all_services()
            
            # Generate periodic report
            if time.time() - last_report_time > report_interval:
                report = monitor.generate_health_report(results)
                logger.info(report)
                
                # Write report to file
                report_file = os.path.join(LOG_DIR, "health_report.md")
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Health Report - {datetime.now().isoformat()}\n\n")
                    f.write(report)
                
                last_report_time = time.time()
            
            # Wait for next check
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("Health Monitor stopped by user")
    except Exception as e:
        logger.error(f"Health Monitor crashed: {e}")
        raise


if __name__ == "__main__":
    run_monitor()
