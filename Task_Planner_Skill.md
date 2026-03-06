---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Task Planner Skill

## 1. Skill Name

**Task_Planner**

## 2. Purpose

The Task Planner is a Claude reasoning skill that automatically reads new task files from the `Needs_Action` folder and generates structured `Plan.md` files describing the next steps required to complete each task. This skill transforms raw task requests into actionable, step-by-step plans that guide execution.

**Goal in simple terms:** Read tasks → Think through approach → Write clear plans → Enable execution

## 3. Trigger Condition

The planner activates when:
- A task file with `Status: pending` exists in `Needs_Action/`
- No corresponding plan exists in `Plans/` (checked by `filename` reference)
- Claude Code is invoked to process pending tasks
- The task requires planning before execution (non-trivial tasks)

## 4. Inputs

| Input | Location | Description |
|-------|----------|-------------|
| Task files | `Needs_Action/*.md` | Pending tasks with YAML frontmatter and descriptions |
| Task context | YAML frontmatter | Metadata: Type, Status, Priority, Created_at, Related_files, filename |
| Task content | Markdown body | Description, Checklist, Notes sections |
| Existing plans | `Plans/` | Checked to avoid duplicate planning |

### Task File Structure (Input)

```markdown
---
Type: general_task
Status: pending
Priority: medium
Created_at: <ISO timestamp>
Related_files: ['Inbox/example.txt']
filename: example.txt
---
# Task: Review File 'example.txt'
## Description
A new file was added and requires review.
## Checklist
- [ ] Read the file content
- [ ] Summarize key points
- [ ] Take action if needed
## Notes
(Additional context here)
```

## 5. Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Plan files | `Plans/Plan_<task_name>_<timestamp>.md` | Structured plans with objectives and steps |
| Processing logs | `Logs/System_Log.md` | Timestamped entries for planning actions |
| Console output | Terminal | Real-time status during planning |

### Plan File Structure (Output)

```markdown
---
Type: task_plan
Status: pending
Priority: <inherited from task>
Created_at: <ISO timestamp>
Source_task: <original task filename>
Related_files: [<list of related files>]
---

# Plan: <Task Title>

## Objective
(Clear statement of what success looks like)

## Task Summary
- **Source:** `Needs_Action/<task_file>`
- **Priority:** <priority level>
- **Created:** <timestamp>
- **Context:** (Brief summary of the task background)

## Step-by-Step Actions

### Phase 1: Preparation
- [ ] Step description
- [ ] Resources needed

### Phase 2: Execution
- [ ] Step description
- [ ] Expected outcome

### Phase 3: Verification
- [ ] Step description
- [ ] Success criteria

## Approval Required
(List any steps that require human approval before execution)

## Notes
(Reasoning, assumptions, and context for the plan)
```

## 6. Reasoning Workflow

The Task Planner follows the **Read → Think → Plan → Write** flow:

### Phase 1: READ
```
┌─────────────────────────────────────────┐
│  Read Task Context from Vault           │
├─────────────────────────────────────────┤
│  1. Locate pending task in Needs_Action │
│  2. Parse YAML frontmatter              │
│  3. Extract:                            │
│     - Task title & description          │
│     - Checklist items                   │
│     - Related files                     │
│     - Priority & status                 │
│  4. Check Plans/ for existing plans     │
└─────────────────────────────────────────┘
```

### Phase 2: THINK
```
┌─────────────────────────────────────────┐
│  Analyze & Reason                       │
├─────────────────────────────────────────┤
│  1. What is the core objective?         │
│  2. What information is missing?        │
│  3. What are the dependencies?          │
│  4. What could go wrong?                │
│  5. Which steps need approval?          │
│  6. What is the optimal sequence?       │
└─────────────────────────────────────────┘
```

### Phase 3: PLAN
```
┌─────────────────────────────────────────┐
│  Structure the Plan                     │
├─────────────────────────────────────────┤
│  1. Define clear objective              │
│  2. Break into phases                   │
│  3. Create actionable steps             │
│  4. Identify approval points            │
│  5. Set success criteria                │
│  6. Add relevant notes/context          │
└─────────────────────────────────────────┘
```

### Phase 4: WRITE
```
┌─────────────────────────────────────────┐
│  Generate Plan.md File                  │
├─────────────────────────────────────────┤
│  1. Create file in Plans/ folder        │
│  2. Write YAML frontmatter              │
│  3. Write structured content            │
│  4. Log action to System_Log.md         │
│  5. Output confirmation message         │
└─────────────────────────────────────────┘
```

## 7. Planning Rules

| Rule | Description |
|------|-------------|
| **One plan per task** | Each pending task generates exactly one plan file |
| **No duplicate plans** | Check `Plans/` for existing plans before creating new ones |
| **Preserve task context** | Include source task reference and related files |
| **Clear objectives** | Every plan must have a clearly stated objective |
| **Actionable steps** | Each step must be specific and executable |
| **Phased approach** | Group steps into logical phases (Preparation, Execution, Verification) |
| **Approval flags** | Mark steps requiring human approval explicitly |
| **Status tracking** | Plan status mirrors task status (pending → in-progress → done) |

## 8. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **No direct execution** | Planner only writes plans; does not execute external actions |
| **Human approval required** | Sensitive actions (file deletion, system changes, API calls) must be flagged for approval |
| **Non-destructive** | Planner never modifies source task files |
| **No credential handling** | Plans must not include secrets, API keys, or sensitive data |
| **Log all planning** | Every plan creation is logged to `Logs/System_Log.md` |
| **Respect priorities** | High-priority tasks should be planned first |
| **Graceful degradation** | If task context is incomplete, note assumptions in plan |

### Sensitive Actions Requiring Approval

- File deletion or modification outside `Plans/`
- System configuration changes
- External API calls or network requests
- Database operations
- Credential or secret access
- Code deployment or execution

## 9. Example Flow

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐     ┌──────────┐
│ Needs_Action/   │ ──→ │   Task_Planner      │ ──→ │    Plans/       │ ──→ │   Done/  │
│                 │     │   (Claude Code)     │     │                 │     │          │
│ task_example.md │     │  Read → Think →     │     │ Plan_example.md │     │ task_*.md│
│ (pending task)  │     │  Plan → Write       │     │ (action plan)   │     │ (done)   │
└─────────────────┘     └─────────────────────┘     └─────────────────┘     └──────────┘
       │                        │                          │                     │
       │                        │                          │                     │
       ▼                        ▼                          ▼                     ▼
  Task waiting            Plan generated            Steps executed          Archived
  for planning            with actions              by user/agent           with log
```

### Step-by-Step Example

1. **Task exists:** `Needs_Action/task_review_report.md` with `Status: pending`
2. **Planner reads:**
   - Parses YAML: Priority: high, Related_files: ['Inbox/report.pdf']
   - Reads description: "Review quarterly report and summarize findings"
   - Checks `Plans/` for existing plans → none found
3. **Planner thinks:**
   - Objective: Summarize report findings for stakeholder review
   - Steps needed: Read file, extract data, write summary, flag issues
   - Approval: None required for read/summary operations
4. **Planner writes:** `Plans/Plan_review_report_1708185600.md`
   ```markdown
   ---
   Type: task_plan
   Status: pending
   Priority: high
   Source_task: task_review_report.md
   ---
   # Plan: Review Quarterly Report

   ## Objective
   Produce a concise summary of Q4 report findings for stakeholder distribution.

   ## Step-by-Step Actions
   ### Phase 1: Preparation
   - [ ] Open and read Inbox/report.pdf
   - [ ] Identify key metrics and sections

   ### Phase 2: Execution
   - [ ] Extract financial highlights
   - [ ] Note any anomalies or concerns
   - [ ] Draft summary document

   ### Phase 3: Verification
   - [ ] Review summary for accuracy
   - [ ] Confirm all key points captured
   ```
5. **Agent/User executes:** Follows plan steps, marks complete
6. **Task completed:** Original task moved to `Done/`, plan archived

---

## Related Files

- `process_tasks.py` — Task processor that updates status and moves files
- `file_watcher.py` — Creates tasks from Inbox files
- `Vault_Watcher_Skill.md` — Companion skill for file monitoring
- `Dashboard.md` — Task overview dashboard
- `Logs/System_Log.md` — Activity and planning logs
