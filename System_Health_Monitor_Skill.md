---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# System Health Monitor Skill

## 1. Skill Name

**System_Health_Monitor**

## 2. Purpose

The System Health Monitor skill provides a watchdog monitoring system that ensures all critical AI Employee components (watchers, processors, schedulers) remain active and healthy. It automatically detects crashed processes, restarts them, logs all events, and alerts humans when repeated failures indicate deeper issues.

**Goal in simple terms:** Watch processes → Detect failures → Restart automatically → Alert if persistent

**Core principles:**
- **Continuous monitoring:** Always know system state
- **Automatic recovery:** Self-heal when possible
- **Escalation on pattern:** Alert humans on repeated failures
- **Minimal downtime:** Restart quickly and quietly
- **Full audit trail:** Log everything for debugging

## 3. Monitored Components

### Critical Process List

| Component | Process/Script | Criticality | Auto-Restart |
|-----------|---------------|-------------|--------------|
| **Vault Watcher** | `file_watcher.py` | HIGH | Yes |
| **Task Processor** | `process_tasks.py` | HIGH | Yes |
| **Scheduler Daemon** | `scheduler_daemon.py` | CRITICAL | Yes |
| **Approval Checker** | `approval_checker.py` | MEDIUM | Yes |
| **Log Manager** | `log_manager.py` | LOW | No (non-critical) |
| **Health Monitor** | `health_monitor.py` | CRITICAL | External watchdog |

### Component Health Indicators

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPONENT HEALTH INDICATORS                      │
└─────────────────────────────────────────────────────────────────────┘

  Component: Vault Watcher
  ├── Process Running: YES/NO
  ├── PID: 12345
  ├── Uptime: 2h 34m 12s
  ├── CPU Usage: 0.5%
  ├── Memory Usage: 45 MB
  ├── Last Heartbeat: 2026-02-17T14:30:00
  ├── Files Processed: 156
  ├── Errors (last hour): 0
  └── Status: HEALTHY

  Component: Scheduler Daemon
  ├── Process Running: YES/NO
  ├── PID: 12346
  ├── Uptime: 48h 12m 00s
  ├── CPU Usage: 1.2%
  ├── Memory Usage: 78 MB
  ├── Last Heartbeat: 2026-02-17T14:30:00
  ├── Cycles Completed: 2880
  ├── Errors (last hour): 0
  └── Status: HEALTHY
```

### Health Check Implementation

```python
import psutil
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

class ComponentStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STOPPED = "stopped"

class MonitoredComponent:
    """Represents a component being monitored"""
    
    def __init__(self, name, script_path, criticality, auto_restart=True):
        self.name = name
        self.script_path = Path(script_path)
        self.criticality = criticality  # CRITICAL, HIGH, MEDIUM, LOW
        self.auto_restart = auto_restart
        self.pid = None
        self.process = None
        self.start_time = None
        self.last_heartbeat = None
        self.restart_count = 0
        self.last_restart_time = None
        self.error_count = 0
        self.status = ComponentStatus.UNKNOWN
    
    def find_process(self):
        """Find the running process by script name"""
        script_name = self.script_path.name
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if script_name in cmdline:
                    self.pid = proc.info['pid']
                    self.process = proc
                    self.status = ComponentStatus.HEALTHY
                    self.last_heartbeat = datetime.now()
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Process not found
        self.pid = None
        self.process = None
        self.status = ComponentStatus.STOPPED
        return False
    
    def get_uptime(self):
        """Get component uptime"""
        if not self.start_time:
            return timedelta(0)
        return datetime.now() - self.start_time
    
    def get_metrics(self):
        """Get current resource metrics"""
        if not self.process:
            return {'cpu_percent': 0, 'memory_mb': 0}
        
        try:
            cpu = self.process.cpu_percent(interval=0.1)
            memory = self.process.memory_info().rss / (1024 * 1024)  # MB
            return {'cpu_percent': cpu, 'memory_mb': memory}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {'cpu_percent': 0, 'memory_mb': 0}

class HealthMonitor:
    """Main health monitoring system"""
    
    def __init__(self):
        self.components = {}
        self.alert_threshold = 3  # Alert after N restarts in window
        self.alert_window_minutes = 30
        self.restart_cooldown_seconds = 10  # Prevent rapid restart loops
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize list of components to monitor"""
        self.components = {
            'vault_watcher': MonitoredComponent(
                name='Vault Watcher',
                script_path='file_watcher.py',
                criticality='HIGH',
                auto_restart=True
            ),
            'task_processor': MonitoredComponent(
                name='Task Processor',
                script_path='process_tasks.py',
                criticality='HIGH',
                auto_restart=True
            ),
            'scheduler_daemon': MonitoredComponent(
                name='Scheduler Daemon',
                script_path='scheduler_daemon.py',
                criticality='CRITICAL',
                auto_restart=True
            ),
            'approval_checker': MonitoredComponent(
                name='Approval Checker',
                script_path='approval_checker.py',
                criticality='MEDIUM',
                auto_restart=True
            ),
            'log_manager': MonitoredComponent(
                name='Log Manager',
                script_path='log_manager.py',
                criticality='LOW',
                auto_restart=False
            )
        }
```

## 4. Restart Policy

### Restart Decision Matrix

| Condition | Action | Delay | Notes |
|-----------|--------|-------|-------|
| Process stopped | Restart immediately | 0s | First occurrence |
| Process crashed | Restart with cooldown | 10s | Prevent rapid cycles |
| 2 crashes in 5 min | Restart + log warning | 30s | Investigate cause |
| 3+ crashes in 30 min | Alert human, restart | 60s | Pattern detected |
| Critical component | Always restart | As above | No exceptions |
| Non-critical | Restart 3x max | As above | Then stop |

### Restart Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       RESTART DECISION FLOW                         │
└─────────────────────────────────────────────────────────────────────┘

    Component Health Check
            │
            ▼
    ┌──────────────────┐
    │ Process Running? │
    └────────┬─────────┘
             │
       ┌─────┴─────┐
       │           │
      YES         NO
       │           │
       │           ▼
       │    ┌──────────────────┐
       │    │ Check Restart    │
       │    │ Cooldown         │
       │    └────────┬─────────┘
       │             │
       │             ▼
       │    ┌──────────────────┐
       │    │ Count Recent     │
       │    │ Restarts         │
       │    └────────┬─────────┘
       │             │
       │       ┌─────┴─────┐
       │       │           │
       │    < 3 times   ≥ 3 times
       │       │           │
       │       │           ▼
       │       │    ┌──────────────────┐
       │       │    │ ALERT HUMAN      │
       │       │    │ (Pattern detected)│
       │       │    └────────┬─────────┘
       │       │             │
       │       ▼             ▼
       │    ┌──────────────────┐
       │    │ Check Criticality│
       │    └────────┬─────────┘
       │             │
       │       ┌─────┴─────┐
       │       │           │
       │   CRITICAL     OTHER
       │       │           │
       │       │           ▼
       │       │    ┌──────────────────┐
       │       │    │ Max Restarts     │
       │       │    │ Reached?         │
       │       │    └────────┬─────────┘
       │       │             │
       │       │       ┌─────┴─────┐
       │       │       │           │
       │       │      YES         NO
       │       │       │           │
       │       │       │           ▼
       │       │       │    ┌──────────────────┐
       │       │       │    │ RESTART PROCESS  │
       │       │       │    │ - Spawn new proc │
       │       │       │    │ - Update PID     │
       │       │       │    │ - Log event      │
       │       │       │    └──────────────────┘
       │       │       │
       │       │       ▼
       │       │  ┌──────────────────┐
       │       │  │ Log & Alert      │
       │       │  │ (Max reached)    │
       │       │  └──────────────────┘
       │       │
       ▼       ▼
    ┌──────────────────┐
    │ Continue         │
    │ Monitoring       │
    └──────────────────┘
```

### Restart Implementation

```python
import subprocess
import sys
from collections import deque

class RestartPolicy:
    """Manages restart decisions and execution"""
    
    def __init__(self):
        self.restart_history = {}  # component_name -> deque of timestamps
        self.max_restarts_window = timedelta(minutes=30)
        self.max_restarts_count = 3
        self.cooldown_seconds = 10
        self.last_restart = {}  # component_name -> timestamp
    
    def should_restart(self, component):
        """Determine if a component should be restarted"""
        name = component.name
        
        # Check if auto-restart is enabled
        if not component.auto_restart:
            return False, "Auto-restart disabled"
        
        # Check cooldown
        if name in self.last_restart:
            elapsed = (datetime.now() - self.last_restart[name]).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False, f"Cooldown active ({elapsed:.1f}s elapsed)"
        
        # Count recent restarts
        recent_restarts = self._count_recent_restarts(name)
        
        if recent_restarts >= self.max_restarts_count:
            # Check if critical - always restart critical components
            if component.criticality == 'CRITICAL':
                return True, "Critical component - forced restart"
            else:
                return False, f"Max restarts reached ({recent_restarts})"
        
        return True, "Restart allowed"
    
    def _count_recent_restarts(self, component_name):
        """Count restarts within the alert window"""
        if component_name not in self.restart_history:
            return 0
        
        cutoff = datetime.now() - self.max_restarts_window
        recent = [ts for ts in self.restart_history[component_name] if ts > cutoff]
        return len(recent)
    
    def record_restart(self, component_name):
        """Record a restart event"""
        now = datetime.now()
        
        if component_name not in self.restart_history:
            self.restart_history[component_name] = deque()
        
        self.restart_history[component_name].append(now)
        self.last_restart[component_name] = now
        
        # Clean old entries
        cutoff = now - self.max_restarts_window
        while (self.restart_history[component_name] and 
               self.restart_history[component_name][0] < cutoff):
            self.restart_history[component_name].popleft()
    
    def execute_restart(self, component):
        """Execute the restart of a component"""
        import logging
        logger = logging.getLogger('health_monitor')
        
        logger.info(f"Restarting {component.name}...")
        
        try:
            # Start the process
            process = subprocess.Popen(
                [sys.executable, str(component.script_path)],
                cwd=component.script_path.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Update component state
            component.pid = process.pid
            component.process = process
            component.start_time = datetime.now()
            component.status = ComponentStatus.HEALTHY
            component.restart_count += 1
            component.last_restart_time = datetime.now()
            
            # Record the restart
            self.record_restart(component.name)
            
            logger.info(f"Successfully restarted {component.name} (PID: {process.pid})")
            return True, f"Restarted successfully (PID: {process.pid})"
            
        except Exception as e:
            logger.error(f"Failed to restart {component.name}: {e}")
            return False, f"Restart failed: {e}"
    
    def needs_human_alert(self, component):
        """Check if human alert is needed"""
        recent_restarts = self._count_recent_restarts(component.name)
        return recent_restarts >= self.max_restarts_count
```

## 5. Alert Strategy

### Alert Severity Levels

| Level | Trigger | Method | Urgency |
|-------|---------|--------|---------|
| **INFO** | Normal restart (first occurrence) | Log only | Low |
| **WARNING** | 2 restarts in 5 minutes | Log + Dashboard | Medium |
| **ERROR** | 3+ restarts in 30 minutes | Log + Email/Slack | High |
| **CRITICAL** | Critical component won't start | Log + Immediate notification | Urgent |

### Alert Escalation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                       ALERT ESCALATION FLOW                         │
└─────────────────────────────────────────────────────────────────────┘

  Restart Event
       │
       ▼
  ┌─────────────────┐
  │ Count Restarts  │
  │ (Last 30 min)   │
  └────────┬────────┘
           │
     ┌─────┴─────┬─────────────┐
     │           │             │
    1st        2nd          3rd+
     │           │             │
     ▼           ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐
│  INFO   │ │ WARNING │ │   ERROR     │
│ Log     │ │ Log +   │ │ Log +       │
│ only    │ │ Dashboard│ │ Email/Slack │
└─────────┘ └─────────┘ └──────┬──────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  CRITICAL   │
                        │ Component   │
                        │ Unrecoverable│
                        └──────┬──────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ IMMEDIATE   │
                        │ Phone/SMS   │
                        │ (if config) │
                        └─────────────┘
```

### Alert Implementation

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    """Represents a system alert"""
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime
    restart_count: int = 0
    details: Optional[dict] = None

class AlertManager:
    """Manages alert generation and delivery"""
    
    def __init__(self):
        self.alert_history = []
        self.email_enabled = False
        self.slack_enabled = False
        self.dashboard_file = "Logs/system_health_dashboard.md"
    
    def create_alert(self, component, level, message, restart_count=0, details=None):
        """Create and dispatch an alert"""
        alert = Alert(
            level=level,
            component=component.name,
            message=message,
            timestamp=datetime.now(),
            restart_count=restart_count,
            details=details or {}
        )
        
        self.alert_history.append(alert)
        
        # Dispatch based on level
        if level == AlertLevel.INFO:
            self._log_alert(alert)
        elif level == AlertLevel.WARNING:
            self._log_alert(alert)
            self._update_dashboard(alert)
        elif level == AlertLevel.ERROR:
            self._log_alert(alert)
            self._update_dashboard(alert)
            self._send_notification(alert)
        elif level == AlertLevel.CRITICAL:
            self._log_alert(alert)
            self._update_dashboard(alert)
            self._send_notification(alert, urgent=True)
        
        return alert
    
    def _log_alert(self, alert):
        """Log alert to system log"""
        log_entry = (
            f"[{alert.timestamp.isoformat()}] "
            f"[{alert.level.value.upper()}] "
            f"[{alert.component}] {alert.message}"
        )
        
        with open("Logs/system_health.log", "a") as f:
            f.write(log_entry + "\n")
    
    def _update_dashboard(self, alert):
        """Update the health dashboard file"""
        dashboard_content = self._read_dashboard()
        
        # Add alert to dashboard
        alert_entry = (
            f"\n### {alert.level.value.upper()}: {alert.component}\n"
            f"- **Time:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **Message:** {alert.message}\n"
            f"- **Restart Count:** {alert.restart_count}\n"
        )
        
        # Insert after header
        header_end = dashboard_content.find("## Recent Alerts")
        if header_end == -1:
            header_end = len(dashboard_content)
        
        dashboard_content = (
            dashboard_content[:header_end] + 
            alert_entry + 
            dashboard_content[header_end:]
        )
        
        self._write_dashboard(dashboard_content)
    
    def _send_notification(self, alert, urgent=False):
        """Send notification via configured channels"""
        # Email notification
        if self.email_enabled:
            self._send_email(alert, urgent)
        
        # Slack notification
        if self.slack_enabled:
            self._send_slack(alert, urgent)
    
    def _send_email(self, alert, urgent):
        """Send email notification"""
        import smtplib
        from email.mime.text import MIMEText
        
        subject = f"[{'URGENT' if urgent else 'ALERT'}] System Health: {alert.component}"
        body = f"""
System Health Alert

Component: {alert.component}
Level: {alert.level.value.upper()}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Message: {alert.message}
Restart Count: {alert.restart_count}

Please investigate immediately.
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_FROM')
        msg['To'] = os.getenv('ALERT_EMAIL')
        
        try:
            # Send email (implementation depends on SMTP config)
            pass
        except Exception as e:
            print(f"Failed to send email alert: {e}")
    
    def _send_slack(self, alert, urgent):
        """Send Slack notification"""
        import requests
        
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            return
        
        color = {
            AlertLevel.INFO: "good",
            AlertLevel.WARNING: "warning",
            AlertLevel.ERROR: "danger",
            AlertLevel.CRITICAL: "danger"
        }.get(alert.level, "warning")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"{'🚨 URGENT' if urgent else '⚠️ Alert'}: {alert.component}",
                "fields": [
                    {"title": "Level", "value": alert.level.value.upper(), "short": True},
                    {"title": "Restarts", "value": str(alert.restart_count), "short": True},
                    {"title": "Message", "value": alert.message, "short": False}
                ],
                "ts": int(alert.timestamp.timestamp())
            }]
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
    
    def _read_dashboard(self):
        """Read dashboard file content"""
        try:
            with open(self.dashboard_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return self._create_dashboard_template()
    
    def _write_dashboard(self, content):
        """Write dashboard file content"""
        with open(self.dashboard_file, 'w') as f:
            f.write(content)
    
    def _create_dashboard_template(self):
        """Create new dashboard file"""
        return """# System Health Dashboard

## Current Status
- **Last Updated:** Never
- **Overall Status:** Unknown

## Monitored Components
| Component | Status | PID | Uptime | Restarts |
|-----------|--------|-----|--------|----------|
| Loading... |

## Recent Alerts

"""
```

## 6. Logging Rules

### Log File Structure

| Log File | Purpose | Format |
|----------|---------|--------|
| `Logs/system_health.log` | Main health monitor log | Text with timestamps |
| `Logs/restart_events.jsonl` | All restart events | JSON Lines |
| `Logs/alerts.jsonl` | All alerts generated | JSON Lines |
| `Logs/system_health_dashboard.md` | Human-readable dashboard | Markdown |

### Log Entry Format

```
# system_health.log format
[TIMESTAMP] [LEVEL] [COMPONENT] MESSAGE

# Examples
[2026-02-17T14:30:00.123] [INFO] [Vault_Watcher] Health check passed
[2026-02-17T14:30:05.456] [WARNING] [Task_Processor] Process not found, initiating restart
[2026-02-17T14:30:06.789] [INFO] [Task_Processor] Restart successful (PID: 12347)
[2026-02-17T14:35:00.000] [ERROR] [Scheduler_Daemon] Restart count exceeded threshold (3 in 30min)
```

### JSON Restart Event Format

```json
{
  "timestamp": "2026-02-17T14:30:05.456Z",
  "event_type": "restart",
  "component": "Task_Processor",
  "script_path": "process_tasks.py",
  "previous_pid": 12346,
  "new_pid": 12347,
  "restart_count": 2,
  "restarts_last_30min": 2,
  "reason": "Process not found",
  "cooldown_elapsed": 15.3,
  "result": "success",
  "uptime_before_crash": "2h 15m 30s"
}
```

### Logging Implementation

```python
import json
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging for health monitor"""
    logger = logging.getLogger('health_monitor')
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'Logs/system_health.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger

class RestartEventLogger:
    """Logs restart events in JSON format"""
    
    def __init__(self, log_file='Logs/restart_events.jsonl'):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
    
    def log_restart(self, component, event_data):
        """Log a restart event as JSON"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'restart',
            'component': component.name,
            'script_path': str(component.script_path),
            **event_data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def log_restart_failure(self, component, error):
        """Log a failed restart attempt"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'restart_failure',
            'component': component.name,
            'script_path': str(component.script_path),
            'error': str(error),
            'error_type': type(error).__name__
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
```

## 7. Example Restart Scenario

### Scenario: Vault Watcher Crashes and Restarts

```
┌─────────────────────────────────────────────────────────────────────┐
│              RESTART SCENARIO: VAULT WATCHER CRASH                  │
└─────────────────────────────────────────────────────────────────────┘

  T+0s: HEALTH CHECK
  ┌─────────────────────────────────────────────────────────────────┐
  │ Health Monitor performs routine check                          │
  │ - Scanning for Vault Watcher process...                        │
  │ - Process NOT FOUND (PID 12345 no longer exists)               │
  │ - Status changed: HEALTHY → STOPPED                            │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  T+0.1s: RESTART DECISION
  ┌─────────────────────────────────────────────────────────────────┐
  │ Evaluating restart policy...                                   │
  │ - Auto-restart enabled: YES                                    │
  │ - Cooldown elapsed: YES (no recent restarts)                   │
  │ - Recent restart count: 0                                      │
  │ - Criticality: HIGH                                            │
  │ Decision: RESTART ALLOWED                                      │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  T+0.2s: RESTART EXECUTION
  ┌─────────────────────────────────────────────────────────────────┐
  │ Executing restart...                                           │
  │ Command: python file_watcher.py                                │
  │ New PID: 12400                                                 │
  │ Process started successfully                                   │
  │ Status changed: STOPPED → HEALTHY                              │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  T+0.3s: LOGGING
  ┌─────────────────────────────────────────────────────────────────┐
  │ Recording restart event...                                     │
  │                                                                │
  │ Logs/system_health.log:                                        │
  │ [2026-02-17T14:30:05.123] [INFO] [Vault_Watcher] Process lost  │
  │ [2026-02-17T14:30:05.456] [INFO] [Vault_Watcher] Restart init  │
  │ [2026-02-17T14:30:05.789] [INFO] [Vault_Watcher] Restart OK    │
  │                                                                │
  │ Logs/restart_events.jsonl:                                     │
  │ {"timestamp":"2026-02-17T14:30:05.789Z",                       │
  │  "component":"Vault_Watcher",                                  │
  │  "previous_pid":12345, "new_pid":12400,                        │
  │  "restart_count":1, "result":"success"}                        │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  T+30s: VERIFICATION
  ┌─────────────────────────────────────────────────────────────────┐
  │ Follow-up health check...                                      │
  │ - Process 12400 running: YES                                   │
  │ - Heartbeat received: YES                                      │
  │ - Status: HEALTHY                                              │
  │ Restart successful, system recovered                           │
  └─────────────────────────────────────────────────────────────────┘
```

### Scenario: Repeated Failures Trigger Alert

```
┌─────────────────────────────────────────────────────────────────────┐
│           ALERT SCENARIO: REPEATED SCHEDULER FAILURES               │
└─────────────────────────────────────────────────────────────────────┘

  Timeline of Events:
  
  T+0m:   Scheduler crashes (restart #1)
          → Auto-restart, INFO logged
  
  T+5m:   Scheduler crashes again (restart #2)
          → Auto-restart, WARNING logged
          → Dashboard updated
  
  T+12m:  Scheduler crashes again (restart #3)
          → Auto-restart, ERROR alert triggered
          → Email sent to admin
          → Slack notification posted
  
  T+15m:  Scheduler crashes again (restart #4)
          → CRITICAL alert
          → Immediate notification
          → Human intervention required
```

### Alert Email Example

```
Subject: [ALERT] System Health: Scheduler_Daemon

System Health Alert

Component: Scheduler_Daemon
Level: ERROR
Time: 2026-02-17 14:45:00
Message: Restart count exceeded threshold (3 restarts in 30 minutes)
Restart Count: 3

Recent Restarts:
  1. 2026-02-17 14:15:00 - PID 12346 → 12350
  2. 2026-02-17 14:20:00 - PID 12350 → 12355
  3. 2026-02-17 14:32:00 - PID 12355 → 12360

Please investigate immediately.

Possible causes:
  - Memory leak in scheduler
  - Configuration issue
  - External dependency failure
  - Resource exhaustion

Check Logs/system_health.log for details.
```

### Dashboard After Alert

```markdown
# System Health Dashboard

## Current Status
- **Last Updated:** 2026-02-17 14:45:00
- **Overall Status:** DEGRADED

## Monitored Components
| Component | Status | PID | Uptime | Restarts |
|-----------|--------|-----|--------|----------|
| Scheduler_Daemon | ⚠️ UNSTABLE | 12360 | 13m | 4 |
| Vault_Watcher | ✅ HEALTHY | 12400 | 2h 30m | 1 |
| Task_Processor | ✅ HEALTHY | 12347 | 4h 15m | 0 |
| Approval_Checker | ✅ HEALTHY | 12380 | 1h 45m | 0 |

## Recent Alerts

### ERROR: Scheduler_Daemon
- **Time:** 2026-02-17 14:45:00
- **Message:** Restart count exceeded threshold (3 in 30min)
- **Restart Count:** 3

### WARNING: Scheduler_Daemon
- **Time:** 2026-02-17 14:20:00
- **Message:** Second restart within 5 minutes
- **Restart Count:** 2
```

---

## Folder Structure

```
hackathon-0/
├── Logs/
│   ├── system_health.log         # Main health monitor log
│   ├── restart_events.jsonl      # JSON restart event log
│   ├── alerts.jsonl              # JSON alert log
│   └── system_health_dashboard.md # Human-readable dashboard
├── bronze/
│   ├── System_Health_Monitor_Skill.md  # This skill
│   ├── Scheduler_Daemon_Trigger_Skill.md
│   ├── Error_Recovery_Skill.md
│   └── ...
└── health_monitor.py             # Health monitor implementation
```

## Related Files

- `Scheduler_Daemon_Trigger_Skill.md` — Monitored by health monitor
- `Error_Recovery_Skill.md` — Works with health monitor for recovery
- `Audit_Logging_Skill.md` — Health events logged for audit
- `Human_Approval_Skill.md` — Human alerted on critical failures
