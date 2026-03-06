---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Error Recovery Skill

## 1. Skill Name

**Error_Recovery**

## 2. Purpose

The Error Recovery skill provides a production-grade error handling and recovery mechanism for the Personal AI Employee system. It categorizes errors, implements intelligent retry strategies, ensures graceful degradation when components fail, and escalates unrecoverable issues to humans for resolution.

**Goal in simple terms:** Detect error → Categorize → Retry or recover → Log → Escalate if needed

**Core principles:**
- Never silently fail
- Never retry dangerous actions automatically
- Always preserve task state
- Always log for debugging
- Escalate when recovery is not possible

## 3. Error Categories

| Category | Description | Examples | Retry? |
|----------|-------------|----------|--------|
| **Transient** | Temporary failures that may resolve on their own | Network timeout, file locked, rate limit, API temporarily unavailable | Yes, with backoff |
| **Authentication** | Credential or permission issues | Expired token, invalid API key, access denied | No, escalate |
| **Logic** | Business rule violations or invalid state | Task missing required fields, invalid workflow transition | No, escalate |
| **Data** | Corrupt or malformed data | Invalid YAML, missing required fields, encoding errors | No, escalate |
| **System** | Infrastructure or resource failures | Disk full, out of memory, permission denied | No, alert |

### Error Category Details

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ERROR CATEGORY DECISION TREE                   │
└─────────────────────────────────────────────────────────────────────┘

                              Error Occurs
                                   │
                                   ▼
                          Is it temporary?
                          (network, locked)
                                   │
                          ┌────────┴────────┐
                          │                 │
                         YES               NO
                          │                 │
                          ▼                 ▼
                    ┌──────────┐      Is it auth/permission?
                    │ TRANSIENT│              │
                    │ Retry OK │      ┌───────┴───────┐
                    └──────────┘      │               │
                                     YES             NO
                                      │               │
                                      ▼               ▼
                                ┌──────────┐    Is it data/format?
                                │   AUTH   │            │
                                │ Escalate │    ┌───────┴───────┐
                                └──────────┘    │               │
                                               YES             NO
                                                │               │
                                                ▼               ▼
                                          ┌──────────┐    ┌──────────┐
                                          │  DATA    │    │ SYSTEM   │
                                          │ Escalate │    │ Alert    │
                                          └──────────┘    └──────────┘
```

### Category Reference Table

```yaml
ERROR_CATEGORIES:
  Transient:
    codes: [TIMEOUT, RATE_LIMIT, FILE_LOCKED, TEMP_UNAVAILABLE]
    retry: true
    max_retries: 3
    backoff: exponential
    
  Authentication:
    codes: [AUTH_FAILED, TOKEN_EXPIRED, ACCESS_DENIED, INVALID_CREDENTIALS]
    retry: false
    action: escalate_immediately
    
  Logic:
    codes: [INVALID_STATE, MISSING_FIELD, WORKFLOW_VIOLATION, RULE_VIOLATION]
    retry: false
    action: escalate_to_review
    
  Data:
    codes: [PARSE_ERROR, CORRUPT_FILE, ENCODING_ERROR, SCHEMA_MISMATCH]
    retry: false
    action: escalate_to_review
    
  System:
    codes: [DISK_FULL, OUT_OF_MEMORY, PERMISSION_DENIED, HARDWARE_ERROR]
    retry: false
    action: alert_and_degrade
```

## 4. Retry Strategy

### Exponential Backoff Algorithm

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EXPONENTIAL BACKOFF STRATEGY                     │
└─────────────────────────────────────────────────────────────────────┘

  Attempt 1: Wait 1 second   (2^0 = 1)
      │
      ▼
  Attempt 2: Wait 2 seconds  (2^1 = 2)
      │
      ▼
  Attempt 3: Wait 4 seconds  (2^2 = 4)
      │
      ▼
  Attempt 4: Wait 8 seconds  (2^3 = 8)
      │
      ▼
  Attempt 5: Wait 16 seconds (2^4 = 16) → MAX_RETRIES reached → Escalate

  Formula: wait_time = base_delay * (2 ^ attempt_number)
  Where: base_delay = 1 second, max_retries = 5
```

### Retry Configuration

```python
RETRY_CONFIG = {
    "max_retries": 5,
    "base_delay_seconds": 1,
    "max_delay_seconds": 60,
    "exponential_base": 2,
    "jitter": True,  # Add randomness to prevent thundering herd
}
```

### Retry Implementation

```python
import time
import random

def execute_with_retry(func, error_category, max_retries=5):
    """
    Execute function with exponential backoff retry logic.
    Only applies to Transient errors.
    """
    if error_category != "Transient":
        # Never retry non-transient errors
        return func()
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except TransientError as e:
            last_exception = e
            
            if attempt == max_retries - 1:
                # Max retries reached
                break
            
            # Calculate delay with exponential backoff + jitter
            delay = (2 ** attempt) + random.uniform(0, 1)
            delay = min(delay, 60)  # Cap at 60 seconds
            
            log_retry_attempt(attempt, delay, str(e))
            time.sleep(delay)
    
    # All retries exhausted
    raise MaxRetriesExceeded(f"Failed after {max_retries} attempts", last_exception)
```

### ⚠️ NO-RETRY Actions (Critical Safety Rule)

The following actions MUST NEVER be automatically retried:

| Action Type | Reason | Required Handling |
|-------------|--------|-------------------|
| **Financial/Payments** | Risk of duplicate charges | Human approval for each attempt |
| **Email to external contacts** | Risk of spam/duplicates | Manual review and resend |
| **Social media posts** | Risk of duplicate posts | Human approval required |
| **File deletions** | Data loss risk | Confirmation before retry |
| **Database writes** | Risk of duplicate/corrupt data | Idempotency check required |
| **API calls with side effects** | Unpredictable consequences | Human review |

```python
# NEVER retry these actions automatically
NO_RETRY_ACTIONS = [
    "payment",
    "financial_transaction",
    "external_email",
    "social_media_post",
    "file_delete",
    "database_write",
    "external_api_mutation"
]

def is_safe_to_retry(action_type):
    """Check if action type is safe for automatic retry"""
    if action_type in NO_RETRY_ACTIONS:
        return False
    return True
```

## 5. Graceful Degradation Strategy

When components fail, the system continues operating with reduced functionality:

### Degradation Levels

```
┌─────────────────────────────────────────────────────────────────────┐
│                   GRACEFUL DEGRADATION LEVELS                       │
└─────────────────────────────────────────────────────────────────────┘

  LEVEL 0: FULL OPERATION
  ✓ All components working
  ✓ Normal processing
  
  LEVEL 1: DEGRADED
  ⚠ One non-critical component failed
  ✓ Core functions continue
  ⚠ Some features unavailable
  
  LEVEL 2: LIMITED
  ⚠ Multiple components failed
  ✓ Essential functions only
  ⚠ Queuing tasks for later
  
  LEVEL 3: SAFE MODE
  ⚠ Critical failure detected
  ✓ Logging and monitoring active
  ⚠ Manual intervention required
```

### Component Failure Handling

| Component | Failure Impact | Degradation Action |
|-----------|----------------|-------------------|
| **Vault Watcher** | New files not detected | Queue manual check, alert user |
| **Task Processor** | Tasks not progressing | Move tasks to Review_Required |
| **Approval Checker** | Approved actions stuck | Log, notify pending approvals |
| **Log Manager** | Logs not written | Write to stderr, buffer in memory |
| **Scheduler** | No automatic cycles | Continue manual execution |

### Degradation Implementation

```python
class SystemHealth:
    def __init__(self):
        self.component_status = {
            "vault_watcher": "healthy",
            "task_processor": "healthy",
            "approval_checker": "healthy",
            "log_manager": "healthy",
            "scheduler": "healthy"
        }
    
    def mark_unhealthy(self, component, error):
        """Mark component as unhealthy and trigger degradation"""
        self.component_status[component] = "unhealthy"
        log_error(f"Component {component} marked unhealthy: {error}")
        
        # Trigger degradation strategy
        self.apply_degradation(component)
    
    def apply_degradation(self, failed_component):
        """Apply appropriate degradation strategy"""
        degradation_map = {
            "vault_watcher": self.degrade_vault_watcher,
            "task_processor": self.degrade_task_processor,
            "approval_checker": self.degrade_approval_checker,
            "log_manager": self.degrade_log_manager,
            "scheduler": self.degrade_scheduler
        }
        
        if failed_component in degradation_map:
            degradation_map[failed_component]()
    
    def degrade_task_processor(self):
        """When task processor fails, move tasks to review"""
        move_pending_to_review()
        notify_user("Task processor unavailable. Tasks moved to Review_Required.")
    
    def get_system_level(self):
        """Calculate current degradation level"""
        healthy_count = sum(
            1 for status in self.component_status.values() 
            if status == "healthy"
        )
        
        if healthy_count == 5:
            return 0  # Full operation
        elif healthy_count >= 3:
            return 1  # Degraded
        elif healthy_count >= 1:
            return 2  # Limited
        else:
            return 3  # Safe mode
```

## 6. Escalation to Human

### Escalation Triggers

| Trigger | Action |
|---------|--------|
| Max retries exceeded | Move to Review_Required |
| Authentication error | Move to Review_Required, notify |
| Logic/Data error | Move to Review_Required |
| System error | Alert, move to Review_Required |
| NO-RETRY action failed | Move to Review_Required |
| Claude reasoning failure | Move to Review_Required |

### Review_Required Folder

When tasks cannot be processed automatically, they are moved to `Review_Required/`:

```markdown
---
Type: review_required
Status: pending_review
Priority: high
Created_at: <ISO timestamp>
Original_location: Needs_Action/<task_file>
Error_category: <category>
Error_message: <description>
Retry_count: <number>
---

# Review Required: <Task Name>

## Original Task
(Original task content preserved)

## Error Details
- **Category:** <error category>
- **Message:** <error description>
- **Timestamp:** <when error occurred>
- **Retry Count:** <number of retries attempted>

## Human Action Required

Please review this task and take one of the following actions:

- [ ] Fix the issue and move back to Needs_Action/
- [ ] Mark as complete and move to Done/
- [ ] Reject and move to Rejected/
- [ ] Add notes and re-queue

## Resolution Section (Filled by Human)

**Action taken:** ________________
**Notes:** ________________
**Date:** ________________
```

### Escalation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ESCALATION TO HUMAN FLOW                       │
└─────────────────────────────────────────────────────────────────────┘

    Error Detected
         │
         ▼
    Can it be recovered automatically?
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    Is it a Claude reasoning failure?
    │         │
    │    ┌────┴────┐
    │    │         │
    │   YES       NO
    │    │         │
    │    │         ▼
    │    │    Create review file
    │    │    Move to Review_Required/
    │    │    Notify human
    │    │
    │    ▼
    │    Move task to Review_Required/
    │    Add error context
    │    Log escalation
    │    Notify human
    │
    ▼
    Attempt recovery
         │
         ▼
    Recovery successful?
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    Escalate to human
    ▼
    Continue processing
```

### Notification Methods

```python
def notify_escalation(task_name, error_category, error_message):
    """Notify human of escalated issue"""
    notification = {
        "type": "escalation",
        "task": task_name,
        "category": error_category,
        "message": error_message,
        "location": "Review_Required/",
        "timestamp": datetime.now().isoformat(),
        "urgency": get_urgency(error_category)
    }
    
    # Log the notification
    log_escalation(notification)
    
    # In production, could also:
    # - Send email
    # - Send Slack message
    # - Create system notification
    # - Trigger push notification
    
    print(f"[ESCALATION] Task '{task_name}' requires attention in Review_Required/")
```

## 7. Logging Rules

### Log File Structure

| Log File | Purpose |
|----------|---------|
| `Logs/System_Log.md` | General activity and error summaries |
| `Logs/watcher_errors.log` | Vault Watcher specific errors |
| `Logs/error_recovery.log` | Error recovery actions and retries |
| `Logs/escalations.log` | Human escalation records |

### Error Log Entry Format

```markdown
## Error Entry

### Timestamp
2026-02-17T14:30:00

### Category
Transient

### Component
Vault Watcher

### Error Message
File locked by another process: Inbox/data.txt

### Context
- **File:** Inbox/data.txt
- **Operation:** read
- **Cycle:** cycle_0042

### Retry Information
- **Attempt:** 2 of 5
- **Next retry in:** 2 seconds
- **Backoff multiplier:** 2x

### Resolution
- [ ] Resolved on retry
- [ ] Escalated to human
- [ ] Manual intervention required

### Notes
(File locked due to sync software. Retrying...)
```

### Logging Rules

| Rule | Description |
|------|-------------|
| **Log all errors** | Every error must be logged, even if recovered |
| **Include timestamps** | ISO format timestamps for all entries |
| **Capture context** | File names, operation types, cycle numbers |
| **Record retry attempts** | Track attempt number and delay |
| **Log escalation decisions** | Document why escalation was chosen |
| **Preserve stack traces** | For debugging, include full error details |
| **Categorize clearly** | Each error must have a category label |
| **Link to tasks** | Associate errors with specific task files |

### Log Rotation for Error Logs

```python
def rotate_error_logs():
    """Rotate error logs when they exceed size limit"""
    error_logs = [
        "Logs/error_recovery.log",
        "Logs/escalations.log",
        "Logs/watcher_errors.log"
    ]
    
    for log_file in error_logs:
        check_log_file(log_file, max_size_mb=1)
```

## 8. Example Failure Scenario

### Scenario: Transient Network Error During API Call

```
┌─────────────────────────────────────────────────────────────────────┐
│                  FAILURE SCENARIO: NETWORK TIMEOUT                  │
└─────────────────────────────────────────────────────────────────────┘

  CYCLE: cycle_0042
  TASK: task_send_notification.md
  ACTION: Send Slack notification via API
  
  ┌─────────────────────────────────────────────────────────────────┐
  │ ATTEMPT 1 (T+0s)                                                │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Action: POST to Slack API                                     │
  │ - Result: TIMEOUT after 30 seconds                              │
  │ - Error category: Transient                                     │
  │ - Decision: Retry with backoff                                  │
  │ - Log: "Attempt 1 failed. Retrying in 1s..."                    │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ATTEMPT 2 (T+1s)                                                │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Action: POST to Slack API                                     │
  │ - Result: TIMEOUT after 30 seconds                              │
  │ - Error category: Transient                                     │
  │ - Decision: Retry with backoff                                  │
  │ - Log: "Attempt 2 failed. Retrying in 2s..."                    │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ATTEMPT 3 (T+3s)                                                │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Action: POST to Slack API                                     │
  │ - Result: SUCCESS (200 OK)                                      │
  │ - Decision: Continue processing                                 │
  │ - Log: "Attempt 3 succeeded. Task completed."                   │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ RESOLUTION                                                      │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Task moved to Done/                                           │
  │ - Error logged for reference                                    │
  │ - System continues normal operation                             │
  └─────────────────────────────────────────────────────────────────┘
```

### Scenario: Claude Reasoning Failure

```
┌─────────────────────────────────────────────────────────────────────┐
│              FAILURE SCENARIO: CLAUDE REASONING FAILURE             │
└─────────────────────────────────────────────────────────────────────┘

  CYCLE: cycle_0043
  TASK: task_analyze_report.md
  ACTION: Generate analysis plan using Claude
  
  ┌─────────────────────────────────────────────────────────────────┐
  │ DETECTION (T+0s)                                                │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Claude API returns error or invalid response                  │
  │ - Error category: Logic (reasoning failure)                     │
  │ - Retry allowed: NO (reasoning failures don't resolve on retry) │
  │ - Decision: Escalate to human                                   │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ESCALATION (T+0.5s)                                             │
  ├─────────────────────────────────────────────────────────────────┤
  │ 1. Create review file:                                          │
  │    Review_Required/review_task_analyze_report.md                │
  │                                                                 │
  │ 2. Include error context:                                       │
  │    - Original task content                                      │
  │    - Error message from Claude API                              │
  │    - Timestamp and cycle number                                 │
  │                                                                 │
  │ 3. Move task to Review_Required/                                │
  │                                                                 │
  │ 4. Log escalation                                               │
  │                                                                 │
  │ 5. Notify user: "Task requires manual review"                   │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ HUMAN INTERVENTION (T+5m)                                       │
  ├─────────────────────────────────────────────────────────────────┤
  │ Human reviews task in Review_Required/                          │
  │ Options:                                                        │
  │ - [x] Fix and move to Needs_Action/                             │
  │ - [ ] Complete and move to Done/                                │
  │ - [ ] Reject and move to Rejected/                              │
  │                                                                 │
  │ Human chooses: Move to Needs_Action/ with note                  │
  │ Note: "Retry Claude with simplified prompt"                     │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ RESOLUTION (T+6m)                                               │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Task back in Needs_Action/                                    │
  │ - Will be processed in next cycle                               │
  │ - Escalation logged for analysis                                │
  └─────────────────────────────────────────────────────────────────┘
```

### Scenario: Financial Action Failure (NO RETRY)

```
┌─────────────────────────────────────────────────────────────────────┐
│           FAILURE SCENARIO: PAYMENT PROCESSING ERROR                │
└─────────────────────────────────────────────────────────────────────┘

  CYCLE: cycle_0044
  TASK: task_process_payment.md
  ACTION: Process $500 payment via Stripe API
  
  ┌─────────────────────────────────────────────────────────────────┐
  │ DETECTION (T+0s)                                                │
  ├─────────────────────────────────────────────────────────────────┤
  │ - Action type: financial_transaction                            │
  │ - Result: API error (card declined)                             │
  │ - Error category: Data (invalid card)                           │
  │ - Retry allowed: NO (financial action - safety rule)            │
  │ - Decision: ESCALATE IMMEDIATELY                                │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ ESCALATION (T+0.5s)                                             │
  ├─────────────────────────────────────────────────────────────────┤
  │ ⚠ NO AUTOMATIC RETRY - Financial action                         │
  │                                                                 │
  │ 1. Create review file with URGENT flag                          │
  │ 2. Include payment details (amount, recipient)                  │
  │ 3. Include error message from payment processor                 │
  │ 4. Move to Review_Required/ with high priority                  │
  │ 5. Log: "Payment failed - manual review required"               │
  │ 6. Notify: "URGENT: Payment processing failed"                  │
  └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ HUMAN INTERVENTION REQUIRED                                     │
  ├─────────────────────────────────────────────────────────────────┤
  │ Human must:                                                     │
  │ 1. Contact customer for updated payment info                    │
  │ 2. Verify payment details                                       │
  │ 3. Manually retry or cancel                                     │
  │                                                                 │
  │ ⚠ System will NOT automatically retry payment                   │
  └─────────────────────────────────────────────────────────────────┘
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
├── Review_Required/        # Tasks needing human review (created by this skill)
├── Done/                   # Completed tasks
├── Logs/
│   ├── System_Log.md       # Main activity log
│   ├── watcher_errors.log  # Watcher errors
│   ├── error_recovery.log  # Error recovery actions
│   └── escalations.log     # Human escalation records
└── plants/
    └── task_templete.md    # Task template
```

## Related Files

- `Vault_Watcher_Skill.md` — Monitors Inbox and creates tasks
- `Task_Planner_Skill.md` — Generates plans for tasks
- `Human_Approval_Skill.md` — Human-in-the-Loop approval workflow
- `Scheduler_Daemon_Trigger_Skill.md` — Automated scheduling and execution
- `Company_Handbook.md` — Company rules and guidelines
- `log_manager.py` — Log rotation and management
