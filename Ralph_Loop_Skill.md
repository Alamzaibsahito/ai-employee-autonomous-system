---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-18
---

# Ralph Wiggum Loop Skill (Gold Tier)

## 1. Skill Name

**Ralph_Loop**

## 2. Purpose

The Ralph Wiggum Loop is an autonomous multi-step task execution system that automatically completes tasks by following a continuous cycle: **PLAN → EXECUTE → VERIFY → RETRY OR COMPLETE**.

Named after Ralph Wiggum from The Simpsons (who keeps trying until he succeeds), this loop autonomously executes task steps until the goal is completed or human intervention is required.

**Goal in simple terms:** Read plan → Execute steps → Verify results → Complete or escalate

**Core capabilities:**
- Autonomous step-by-step execution
- Plan parsing and step tracking
- Automatic retry on failure
- Human escalation when needed
- Task completion and archival

## 3. Trigger Conditions

The Ralph Loop activates when:

| Trigger | Description |
|---------|-------------|
| **Scheduler Cycle** | Runs automatically on scheduler intervals |
| **Task with Plan** | Task file exists in `Needs_Action/` with corresponding plan in `Plans/` |
| **Manual Invocation** | Called directly via `run_ralph_loop()` |
| **Post-Approval** | After human approval granted for pending actions |

## 4. The Loop Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      RALPH WIGGUM LOOP CYCLE                            │
└─────────────────────────────────────────────────────────────────────────┘

     ┌─────────────┐
     │    START    │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │  FIND TASK  │
     │  WITH PLAN  │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │  GET NEXT   │
     │   PENDING   │
     │    STEP     │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │   NO STEP   │──────────────────┐
     │  PENDING?   │                  │
     └──────┬──────┘                  │
            │                        YES
           NO                        │
            │                        ▼
            │                 ┌─────────────┐
            │                 │   MARK      │
            │                 │  COMPLETE   │
            │                 │  MOVE TO    │
            │                 │   DONE/     │
            │                 └─────────────┘
            │
            ▼
     ┌─────────────┐
     │  EXECUTE    │
     │    STEP     │
     └──────┬──────┘
            │
            ▼
     ┌─────────────┐
     │  VERIFY     │
     │   RESULT    │
     └──────┬──────┘
            │
    ┌───────┴───────┐
    │               │
  SUCCESS         FAILURE
    │               │
    │               ▼
    │         ┌─────────────┐
    │         │  RETRY?     │
    │         └──────┬──────┘
    │                │
    │         ┌──────┴──────┐
    │         │             │
    │        YES           NO
    │         │             │
    │         │             ▼
    │         │       ┌─────────────┐
    │         │       │ ESCALATE TO │
    │         │       │   HUMAN     │
    │         │       │  REVIEW     │
    │         │       └─────────────┘
    │         │
    │         ▼
    │    ┌─────────────┐
    │    │   RETRY     │
    │    │   STEP      │
    │    └──────┬──────┘
    │           │
    │           ▼
    │     (back to VERIFY)
    │
    ▼
 ┌─────────────┐
 │   MARK      │
 │   STEP      │
 │  COMPLETE   │
 └──────┬──────┘
        │
        ▼
  (back to GET NEXT STEP)
```

## 5. Inputs

| Input | Location | Description |
|-------|----------|-------------|
| Task files | `Needs_Action/*.md` | Pending tasks with status `pending` or `in_progress` |
| Plan files | `Plans/*.md` | Generated plans with step-by-step actions |
| Error recovery | `skills/error_recovery.py` | Retry logic and error handling |
| MCP servers | `mcp_servers/` | External action execution |

### Plan File Structure (Expected Input)

```markdown
---
Type: task_plan
Status: pending
Priority: medium
Source_task: task_example.md
---

# Plan: Example Task

## Step-by-Step Actions

### Phase 1: Preparation
- [ ] Read the file content
- [ ] Identify key information

### Phase 2: Execution
- [ ] Process the data
- [ ] Generate output

### Phase 3: Verification
- [ ] Verify output is correct
- [ ] Mark task complete
```

## 6. Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Completed tasks | `Done/` | Tasks with all steps completed |
| Review required | `Review_Required/` | Tasks that failed and need human help |
| Updated plans | `Plans/` | Plans with completed steps marked |
| Approval requests | `Pending_Approval/` | Steps requiring human approval |
| System log | `Logs/System_Log.md` | Loop execution records |

### Task Completion Output

When a task is completed:
1. Status changed to `done`
2. File moved to `Done/` folder
3. Plan updated with all steps marked complete
4. Entry logged in `System_Log.md`

### Escalation Output

When a task fails:
1. Review file created in `Review_Required/`
2. Original task removed from `Needs_Action/`
3. Error details included in review file
4. Human notification triggered

## 7. Step Execution Types

The loop recognizes different step types and executes them appropriately:

| Step Type | Keywords | Execution |
|-----------|----------|-----------|
| **File Operation** | read, write, create, delete, move, file | File system operations |
| **MCP Action** | email, send, post, linkedin, gmail, api | MCP server calls |
| **Approval Required** | human approval, requires approval, authorize | Creates approval request |
| **Accounting** | payment, invoice, expense, income | Accounting module calls |
| **Generic** | (any other step) | Mark as complete |

## 8. Retry Logic

### Automatic Retry

| Condition | Action |
|-----------|--------|
| Step fails (first time) | Retry once automatically |
| Step fails (after retry) | Escalate to human review |
| Max iterations reached | Escalate to human review |

### Retry Configuration

```python
LOOP_CONFIG = {
    "max_iterations_per_task": 10,  # Prevent infinite loops
    "max_retries_per_step": 1,      # One automatic retry
    "log_every_step": True,         # Log each step execution
}
```

### No-Retry Actions

The following actions are NOT automatically retried (require human approval):
- External emails
- Social media posts
- Financial transactions
- File deletions

## 9. Failure Handling

### Failure Categories

| Category | Response |
|----------|----------|
| **Transient Error** | Retry once, then escalate |
| **Approval Pending** | Wait for human approval |
| **Max Retries** | Escalate to Review_Required |
| **Max Iterations** | Escalate to Review_Required |

### Escalation Process

```
┌─────────────────────────────────────────────────────────────┐
│                    ESCALATION FLOW                          │
└─────────────────────────────────────────────────────────────┘

  Step Failed
       │
       ▼
  Retry Count < Max?
       │
  ┌────┴────┐
  │         │
 YES       NO
  │         │
  │         ▼
  │    Create Review File
  │    Move to Review_Required/
  │    Include Error Details
  │    Remove Original Task
  │
  ▼
  Retry Step
       │
       ▼
  (back to Verify)
```

### Review File Structure

```markdown
---
Type: review_required
Status: pending_review
Priority: high
Created_at: 2026-02-18T10:00:00
Original_task: task_example.md
Error_reason: Max retries exceeded
---

# Review Required: task_example.md

## Original Task
(Original task content preserved)

## Error Details
- **Reason:** Max retries exceeded
- **Completion:** 66.7%
- **Steps completed:** 4 / 6

## Human Action Required

Please review this task and take one of the following actions:

- [ ] Fix the issue and move back to Needs_Action/
- [ ] Mark as complete and move to Done/
- [ ] Reject and move to Rejected/
```

## 10. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **Max iterations** | Loop stops after 10 iterations per task |
| **No infinite loops** | Iteration counter prevents runaway execution |
| **Safe stop** | Loop stops gracefully if no next step exists |
| **Error isolation** | One task failure doesn't stop other tasks |
| **Approval required** | Sensitive actions require human approval |
| **Logged execution** | Every step is logged for audit trail |

### Infinite Loop Prevention

```python
iterations = 0
max_iterations = 10

while iterations < max_iterations:
    iterations += 1
    # Execute step...
    
# If we reach here, max iterations exceeded
escalate_task()
```

## 11. Integration Rules

### With Planner

```
Task Planner → Creates Plan.md → Ralph Loop → Executes Steps
```

The Ralph Loop reads plans generated by the Task Planner skill.

### With Error Recovery

```
Ralph Loop → Step Fails → Error Recovery → Retry or Escalate
```

All step executions are wrapped with error recovery.

### With MCP Servers

```
Ralph Loop → MCP Step → Call MCP Server → Execute Action
```

MCP actions are called for external operations (email, posts).

### With Human Approval

```
Ralph Loop → Approval Step → Create Request → Wait for Human → Continue
```

Approval steps create requests in `Pending_Approval/`.

### With Scheduler

```
Scheduler → Trigger Ralph Loop → Process Tasks → Report Results
```

The scheduler triggers the loop on configured intervals.

## 12. Example Flows

### Example 1: Successful Task Completion

```
┌─────────────────────────────────────────────────────────────────┐
│              SUCCESSFUL TASK COMPLETION FLOW                    │
└─────────────────────────────────────────────────────────────────┘

  TASK: task_process_file.md
  PLAN: Plan_process_file.md (6 steps)

  CYCLE 1:
  - Step 1: Read file content → SUCCESS ✓
  - Step 2: Identify key info → SUCCESS ✓
  - Step 3: Process data → SUCCESS ✓
  - Step 4: Generate output → SUCCESS ✓
  - Step 5: Verify output → SUCCESS ✓
  - Step 6: Mark complete → SUCCESS ✓

  RESULT:
  - All steps completed
  - Task moved to Done/
  - Status: done
  - Plan updated with all checkmarks
```

### Example 2: Step Failure with Recovery

```
┌─────────────────────────────────────────────────────────────────┐
│                  FAILURE AND RECOVERY FLOW                      │
└─────────────────────────────────────────────────────────────────┘

  TASK: task_send_email.md
  PLAN: Plan_send_email.md (4 steps)

  CYCLE 1:
  - Step 1: Read email content → SUCCESS ✓
  - Step 2: Prepare email → SUCCESS ✓
  - Step 3: Send via MCP → FAILURE (timeout)
    → Retry 1...
    → FAILURE (timeout again)
    → ESCALATE to Review_Required/
  
  RESULT:
  - Task escalated to human
  - Review file created
  - Original task removed
  - Human must decide next action
```

### Example 3: Approval Required

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPROVAL WORKFLOW                            │
└─────────────────────────────────────────────────────────────────┘

  TASK: task_post_linkedin.md
  PLAN: Plan_post_linkedin.md (3 steps)

  CYCLE 1:
  - Step 1: Generate post content → SUCCESS ✓
  - Step 2: Get human approval → APPROVAL REQUIRED
    → Create approval request
    → Move to Pending_Approval/
    → PAUSE execution

  HUMAN ACTION:
  - Reviews approval request
  - Moves file to Approved/

  CYCLE 2 (after approval):
  - Step 2: Get human approval → APPROVED ✓
  - Step 3: Post to LinkedIn → SUCCESS ✓

  RESULT:
  - Task completed
  - Posted to LinkedIn
  - Moved to Done/
```

## 13. Usage Examples

### Run One Cycle

```python
from skills.ralph_loop import run_ralph_loop

# Execute one cycle of the loop
result = run_ralph_loop()

print(f"Tasks processed: {result['tasks_processed']}")
print(f"Tasks completed: {result['tasks_completed']}")
print(f"Tasks failed: {result['tasks_failed']}")
```

### Run Continuous Cycles

```python
from skills.ralph_loop import run_ralph_loop_continuous

# Run 10 cycles with 5 second delay between each
run_ralph_loop_continuous(cycles=10, delay_seconds=5)
```

### Use RalphLoop Class Directly

```python
from skills.ralph_loop import RalphLoop

# Create loop instance
loop = RalphLoop()

# Run cycle and get detailed results
result = loop.run_cycle()

print(f"Cycle {result['cycle']} completed")
print(f"Steps executed: {result['steps_executed']}")
```

### Parse Plan Programmatically

```python
from skills.ralph_loop import PlanParser

# Read plan file
with open('Plans/Plan_example.md', 'r') as f:
    plan_content = f.read()

# Parse plan
plan = PlanParser(plan_content)

# Get pending steps
pending = plan.get_pending_steps()
print(f"Pending steps: {len(pending)}")

# Get completion percentage
completion = plan.get_completion_percentage()
print(f"Completion: {completion:.1f}%")

# Mark step as completed
plan.mark_step_completed(0)
```

## 14. Logging

### Log Entry Format

```
[2026-02-18T10:30:13.783] Ralph Loop Cycle 1 starting...
[2026-02-18T10:30:13.789] Executing step 1: Read the test file content
[2026-02-18T10:30:13.791] Step completed: Read the test file content
[2026-02-18T10:30:13.800] Task task_test_ralph_loop.md - All steps completed!
[2026-02-18T10:30:13.802] Task task_test_ralph_loop.md moved to Done folder
```

### System Log Entry

```markdown
[2026-02-18T10:30:13.802] RALPH_LOOP | Task completed: task_test_ralph_loop.md | Steps: 6 | Completion: 100%
```

## 15. Related Files

- `Task_Planner_Skill.md` — Generates plans that Ralph Loop executes
- `Error_Recovery_Skill.md` — Error handling and retry logic
- `Human_Approval_Skill.md` — Approval workflow integration
- `Scheduler_Daemon_Trigger_Skill.md` — Scheduled loop execution
- `skills/error_recovery.py` — Error recovery module
- `skills/ralph_loop.py` — Ralph Loop implementation

## 16. Quick Reference

### Loop Cycle Steps

```
1. Find tasks with plans
2. Get next pending step
3. Execute step
4. Verify result
5. Mark complete or retry
6. Repeat until all steps done
7. Move task to Done/
```

### Configuration

```python
LOOP_CONFIG = {
    "max_iterations_per_task": 10,
    "max_retries_per_step": 1,
    "log_every_step": True,
}
```

### Functions

```python
run_ralph_loop()                    # Run one cycle
run_ralph_loop_continuous(n, delay) # Run n cycles with delay
RalphLoop().run_cycle()             # Run cycle via class
```

### Folders

| Folder | Purpose |
|--------|---------|
| `Needs_Action/` | Pending tasks |
| `Plans/` | Task plans |
| `Done/` | Completed tasks |
| `Review_Required/` | Failed tasks needing review |
| `Pending_Approval/` | Awaiting approval |
| `Approved/` | Approved actions |
