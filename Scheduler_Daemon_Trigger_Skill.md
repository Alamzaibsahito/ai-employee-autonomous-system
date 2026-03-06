---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Scheduler / Daemon Trigger Skill

## 1. Skill Name

**Scheduler_Daemon**

## 2. Purpose

The Scheduler/Daemon skill provides automated, continuous execution of the Vault Watcher and Task Processing workflow at regular intervals without manual intervention. It acts as the central orchestrator that keeps the Personal AI Employee system running 24/7, ensuring no tasks are missed and all workflows progress automatically.

**Goal in simple terms:** Wake up → Run workflows → Log results → Sleep → Repeat

**Core capabilities:**
- Interval-based scheduling (configurable timing)
- Continuous background operation (daemon mode)
- Automatic triggering of Watcher, Planner, and Approval Checker
- Graceful shutdown on demand
- Persistent logging and error recovery

## 3. Trigger Type

### Supported Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Interval** | Runs every N minutes/seconds | Regular task processing (e.g., every 1 minute) |
| **Continuous** | Runs in a loop with sleep between cycles | 24/7 background daemon operation |
| **On-Demand** | Triggered manually or by external event | Testing, urgent processing |

### Configuration

```python
# Scheduler Configuration
SCHEDULER_CONFIG = {
    "mode": "continuous",           # interval | continuous | on-demand
    "interval_seconds": 60,         # How often to run (for interval mode)
    "sleep_between_cycles": 5,      # Seconds to sleep between cycles
    "max_cycles": None,             # None = run forever, or set a number
    "log_every_cycle": True,        # Log each execution cycle
    "graceful_shutdown": True,      # Handle Ctrl+C safely
}
```

### Trigger Schedule

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULER TIMELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  T+0s    T+60s   T+120s   T+180s   T+240s   T+300s             │
│   │       │        │        │        │        │                 │
│   ▼       ▼        ▼        ▼        ▼        ▼                 │
│ ┌───┐   ┌───┐    ┌───┐    ┌───┐    ┌───┐    ┌───┐             │
│ │RUN│──▶│SLEEP│──▶│RUN│──▶│SLEEP│──▶│RUN│──▶│SLEEP│──▶ ...    │
│ └───┘   └───┘    └───┘    └───┘    └───┘    └───┘             │
│                                                                 │
│  Each RUN cycle executes:                                       │
│  1. Vault Watcher (check Inbox for new files)                  │
│  2. Task Processor (process Needs_Action tasks)                │
│  3. Approval Checker (check Approved/ for ready actions)       │
│  4. Log results to Logs/System_Log.md                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Components Triggered

The Scheduler orchestrates three main components in each cycle:

### Component Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    SCHEDULER ORCHESTRATION                       │
└──────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │  SCHEDULER  │
     │   DAEMON    │
     └──────┬──────┘
            │
            ▼
     ┌─────────────────────────────────────────────────────────┐
     │                    CYCLE START                          │
     └─────────────────────────────────────────────────────────┘
            │
            ▼
     ┌─────────────────┐
     │  1. VAULT       │
     │     WATCHER     │◄── file_watcher.py
     │                 │    - Scan Inbox/
     │                 │    - Create tasks in Needs_Action/
     └────────┬────────┘    - Log new detections
              │
              ▼
     ┌─────────────────┐
     │  2. TASK        │
     │     PROCESSOR   │◄── process_tasks.py
     │                 │    - Process Needs_Action/ tasks
     │                 │    - Update status, move to Done/
     └────────┬────────┘    - Update Dashboard.md
              │
              ▼
     ┌─────────────────┐
     │  3. APPROVAL    │
     │     CHECKER     │◄── approval_checker.py
     │                 │    - Check Approved/ folder
     │                 │    - Execute approved actions
     └────────┬────────┘    - Move completed to Done/
              │
              ▼
     ┌─────────────────┐
     │  4. LOGGING     │
     │     MANAGER     │◄── log_manager.py
     │                 │    - Write cycle summary
     │                 │    - Rotate logs if needed
     └────────┬────────┘    - Report errors
              │
              ▼
     ┌─────────────────┐
     │   CYCLE END     │
     │   (Sleep N sec) │
     └─────────────────┘
```

### Component Details

| Component | Script | Responsibility |
|-----------|--------|----------------|
| **Vault Watcher** | `file_watcher.py` | Monitor Inbox/, create tasks in Needs_Action/ |
| **Task Processor** | `process_tasks.py` | Process pending tasks, update status, move to Done/ |
| **Approval Checker** | `approval_checker.py` | Check Approved/, execute approved actions safely |
| **Log Manager** | `log_manager.py` | Write logs, rotate large log files |

## 5. Execution Flow

### Main Cycle Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DAEMON MAIN LOOP                             │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │  while running:                                             │
    │                                                             │
    │      ▼                                                      │
    │  ┌──────────────────┐                                       │
    │  │ CYCLE START      │                                       │
    │  │ timestamp = now  │                                       │
    │  └────────┬─────────┘                                       │
    │           │                                                 │
    │           ▼                                                 │
    │  ┌──────────────────┐                                       │
    │  │ 1. SCAN          │                                       │
    │  │    - Check Inbox/│                                       │
    │  │    - List files  │                                       │
    │  └────────┬─────────┘                                       │
    │           │                                                 │
    │           ▼                                                 │
    │  ┌──────────────────┐                                       │
    │  │ 2. PLAN          │                                       │
    │  │    - Identify    │                                       │
    │  │      new tasks   │                                       │
    │  │    - Generate    │                                       │
    │  │      plans       │                                       │
    │  └────────┬─────────┘                                       │
    │           │                                                 │
    │           ▼                                                 │
    │  ┌──────────────────┐                                       │
    │  │ 3. EXECUTE       │                                       │
    │  │    - Process     │                                       │
    │  │      tasks       │                                       │
    │  │    - Check       │                                       │
    │  │      approvals   │                                       │
    │  └────────┬─────────┘                                       │
    │           │                                                 │
    │           ▼                                                 │
    │  ┌──────────────────┐                                       │
    │  │ 4. LOG           │                                       │
    │  │    - Write cycle │                                       │
    │  │      summary     │                                       │
    │  │    - Record      │                                       │
    │  │      errors      │                                       │
    │  └────────┬─────────┘                                       │
    │           │                                                 │
    │           ▼                                                 │
    │  ┌──────────────────┐                                       │
    │  │ SLEEP            │                                       │
    │  │ (interval sec)   │                                       │
    │  └──────────────────┘                                       │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
```

### Pseudocode Implementation

```python
import time
import signal
import sys
from datetime import datetime

class SchedulerDaemon:
    def __init__(self, interval_seconds=60):
        self.interval = interval_seconds
        self.running = True
        self.cycle_count = 0
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
    
    def shutdown_handler(self, signum, frame):
        """Handle Ctrl+C and termination signals gracefully"""
        print("\n[SHUTDOWN] Received termination signal...")
        self.running = False
    
    def run_cycle(self):
        """Execute one complete processing cycle"""
        cycle_start = datetime.now()
        cycle_id = f"cycle_{self.cycle_count}"
        
        try:
            # Step 1: Run Vault Watcher
            new_files = self.run_vault_watcher()
            
            # Step 2: Run Task Processor
            processed_tasks = self.run_task_processor()
            
            # Step 3: Run Approval Checker
            executed_actions = self.run_approval_checker()
            
            # Step 4: Log cycle results
            self.log_cycle(cycle_id, cycle_start, {
                "new_files": new_files,
                "processed_tasks": processed_tasks,
                "executed_actions": executed_actions,
                "status": "success"
            })
            
        except Exception as e:
            # Log error but continue running
            self.log_error(cycle_id, str(e))
        
        self.cycle_count += 1
    
    def run(self):
        """Main daemon loop"""
        print(f"[DAEMON] Starting scheduler (interval: {self.interval}s)")
        print(f"[DAEMON] Press Ctrl+C to stop")
        
        while self.running:
            self.run_cycle()
            
            # Sleep between cycles (with interruptible sleep)
            for _ in range(self.interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)
        
        print("[DAEMON] Scheduler stopped gracefully")
        print(f"[DAEMON] Total cycles completed: {self.cycle_count}")
```

## 6. Logging Rules

### Log File Locations

| Log File | Purpose |
|----------|---------|
| `Logs/System_Log.md` | Main activity log, cycle summaries |
| `Logs/watcher_errors.log` | Vault Watcher specific errors |
| `Logs/scheduler.log` | Scheduler daemon events |
| `Logs/approval.log` | Approval workflow events |

### Log Entry Format

```markdown
## Cycle Log

### Cycle: cycle_0042
- **Timestamp:** 2026-02-17T14:30:00
- **Duration:** 2.3 seconds
- **Status:** SUCCESS

#### Actions Taken
| Component | Result | Details |
|-----------|--------|---------|
| Vault Watcher | OK | 0 new files detected |
| Task Processor | OK | 2 tasks processed |
| Approval Checker | OK | 1 action executed |

#### Notes
- All components completed successfully
- No errors encountered
```

### Logging Rules

| Rule | Description |
|------|-------------|
| **Log every cycle** | Each execution cycle must be logged, even if no actions taken |
| **Include timestamps** | All log entries must have ISO format timestamps |
| **Record cycle duration** | Track how long each cycle takes |
| **Summarize actions** | List count of files/tasks/actions processed |
| **Capture errors** | All errors logged with full context |
| **Rotate large logs** | Use `log_manager.py` to rotate logs exceeding size limit |
| **Preserve history** | Archived logs kept with timestamp suffix |

### Log Rotation

```
When System_Log.md > 1MB:
1. Rename to System_Log_2026-02-17_143000.md
2. Create new empty System_Log.md
3. Continue logging to new file
4. Keep archived logs for 30 days
```

## 7. Error Handling Strategy

### Error Categories

| Category | Examples | Response |
|----------|----------|----------|
| **Transient** | File locked, network timeout | Retry next cycle |
| **Configuration** | Missing folder, bad config | Log error, continue with defaults |
| **Fatal** | Disk full, permission denied | Log error, continue running, alert user |
| **Data** | Corrupt file, invalid format | Skip file, log warning, continue |

### Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  ERROR HANDLING STRATEGY                    │
└─────────────────────────────────────────────────────────────┘

    Error Detected
         │
         ▼
    ┌─────────────────┐
    │ Categorize Error│
    └────────┬────────┘
             │
    ┌────────┼────────┐
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌──────────┐
│TRANSIENT│ │CONFIG │ │ FATAL   │
└───┬───┘ └───┬───┘ └────┬─────┘
    │         │          │
    ▼         ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Log error│ │ Log error│ │ Log error    │
│ Retry    │ │ Use      │ │ Alert user   │
│ next     │ │ defaults │ │ Continue     │
│ cycle    │ │ Continue │ │ running      │
└──────────┘ └──────────┘ └──────────────┘
```

### Graceful Degradation

```python
def safe_execute(component_func, component_name):
    """Execute component with error isolation"""
    try:
        return component_func()
    except FileNotFoundError as e:
        log_error(f"{component_name}: File not found - {e}")
        return {"status": "skipped", "reason": "file_not_found"}
    except PermissionError as e:
        log_error(f"{component_name}: Permission denied - {e}")
        return {"status": "failed", "reason": "permission_denied"}
    except Exception as e:
        log_error(f"{component_name}: Unexpected error - {e}")
        return {"status": "error", "reason": str(e)}
```

### Recovery Behavior

| Scenario | Recovery Action |
|----------|-----------------|
| Component crashes | Continue with other components, retry next cycle |
| File locked | Skip file, retry next cycle |
| Folder missing | Create folder, continue |
| Log file full | Rotate log, continue |
| Signal received | Complete current cycle, shutdown gracefully |

## 8. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **No sensitive actions without approval** | Approval Checker validates all sensitive actions against Human_Approval_Skill |
| **No destructive actions** | File deletion requires explicit approval workflow |
| **Graceful shutdown only** | Daemon completes current cycle before stopping |
| **Error isolation** | One component failure does not stop other components |
| **No infinite loops** | Sleep between cycles prevents CPU exhaustion |
| **Duplicate prevention** | Processed files tracked to prevent re-processing |
| **Resource limits** | Log rotation prevents disk exhaustion |
| **Signal handling** | Ctrl+C and SIGTERM handled safely |

### Approval Integration

```
┌─────────────────────────────────────────────────────────────┐
│           SENSITIVE ACTION CHECK (Before Execution)         │
└─────────────────────────────────────────────────────────────┘

    Action Identified
         │
         ▼
    Is Action Sensitive?
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    Execute Normally
    │
    ▼
    Check Approval Status
         │
    ┌────┼────────────────────┐
    │    │                    │
    ▼    ▼                    ▼
Approved/  Pending_Approval/  Rejected/
    │         │                    │
    │         │                    │
    ▼         ▼                    ▼
Execute    Wait (Skip)        Skip & Log
 & Log
```

### Shutdown Safety

```python
def shutdown_handler(signum, frame):
    """Ensure graceful shutdown"""
    global running
    
    print("\n[SHUTDOWN] Initiated...")
    print("[SHUTDOWN] Completing current cycle...")
    
    # Set flag to stop after current cycle
    running = False
    
    # Do NOT:
    # - Kill processes mid-operation
    # - Leave files in inconsistent state
    # - Lose processed data
    
    # DO:
    # - Let current cycle finish
    # - Flush all logs
    # - Report final status
```

## 9. Example Cycle

### Complete Cycle Walkthrough

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CYCLE EXECUTION EXAMPLE                      │
└─────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │  WAKE (T+0s)                                                │
    │  - Scheduler daemon wakes from sleep                        │
    │  - Cycle counter: cycle_0042                                │
    │  - Timestamp: 2026-02-17T14:30:00                           │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  SCAN (T+0.1s)                                              │
    │  - Check Inbox/ folder                                      │
    │  - Files found: client_brief.txt (NEW!)                     │
    │  - Check processed set: not found → create task             │
    │  - Task created: task_client_brief_1708185600.md            │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  PLAN (T+0.5s)                                              │
    │  - New task detected in Needs_Action/                       │
    │  - Task type: general_task (no approval needed initially)   │
    │  - Plan generated: Plan_client_brief_1708185600.md          │
    │  - Plan stored in Plans/ folder                             │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  EXECUTE (T+1.0s)                                           │
    │  - Process existing tasks in Needs_Action/                  │
    │  - Task A: Checklist complete → move to Done/               │
    │  - Task B: Requires approval → check Approved/              │
    │  - Task B: Found in Approved/ → execute action              │
    │  - Task B: Move to Done/, log completion                    │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  LOG (T+1.5s)                                               │
    │  - Write cycle summary to Logs/System_Log.md                │
    │  - Record: 1 new file, 2 tasks processed, 1 action executed │
    │  - Check log size: within limits                            │
    │  - Cycle duration: 1.5 seconds                              │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  SLEEP (T+1.5s → T+61.5s)                                   │
    │  - Sleep for 60 seconds                                     │
    │  - Monitor for shutdown signals                             │
    │  - Wake at T+61.5s for next cycle                           │
    └─────────────────────────────────────────────────────────────┘
```

### Sample Log Output

```markdown
## Cycle: cycle_0042
- **Timestamp:** 2026-02-17T14:30:00
- **Duration:** 1.5 seconds
- **Status:** SUCCESS

#### Actions Taken
| Component | Result | Details |
|-----------|--------|---------|
| Vault Watcher | OK | 1 new file (client_brief.txt) |
| Task Processor | OK | 2 tasks processed |
| Approval Checker | OK | 1 action executed (email sent) |

#### Files Created
- `Needs_Action/task_client_brief_1708185600.md`
- `Plans/Plan_client_brief_1708185600.md`

#### Files Moved
- `Needs_Action/task_completed_*.md` → `Done/`

#### Notes
- New client brief detected and task created
- Pending approval action executed successfully
- All components completed without errors
```

---

## Folder Structure

```
hackathon-0/
├── Inbox/                  # New files dropped here
├── Needs_Action/           # Pending tasks
├── Plans/                  # Generated plans
├── Pending_Approval/       # Awaiting human approval
├── Approved/               # Approved actions ready
├── Rejected/               # Denied actions
├── Done/                   # Completed tasks
├── Logs/
│   ├── System_Log.md       # Main activity log
│   ├── watcher_errors.log  # Watcher errors
│   ├── scheduler.log       # Scheduler events
│   └── approval.log        # Approval workflow log
├── plants/
│   └── task_templete.md    # Task template
├── file_watcher.py         # Vault Watcher
├── process_tasks.py        # Task Processor
├── log_manager.py          # Log Manager
└── scheduler_daemon.py     # Scheduler Daemon (this skill)
```

## Related Files

- `Vault_Watcher_Skill.md` — Monitors Inbox and creates tasks
- `Task_Planner_Skill.md` — Generates plans for tasks
- `Human_Approval_Skill.md` — Human-in-the-Loop approval workflow
- `file_watcher.py` — Vault Watcher implementation
- `process_tasks.py` — Task Processor implementation
- `log_manager.py` — Log rotation and management
- `Company_Handbook.md` — Company rules and guidelines
