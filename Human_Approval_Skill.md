---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Human Approval Skill

## 1. Skill Name

**Human_Approval**

## 2. Purpose

The Human Approval skill implements a Human-in-the-Loop (HITL) safety mechanism where Claude Code must obtain explicit human approval before executing sensitive or potentially risky actions. Instead of performing these actions directly, Claude creates approval request files that humans review and either approve or reject.

**Goal in simple terms:** Sensitive action detected → Request approval → Human decides → Proceed or stop

**Core principle:** Claude does NOT directly execute sensitive actions. All such actions require explicit human authorization via file movement in the vault.

## 3. Trigger Condition

The approval workflow activates when:
- A task requires a sensitive action (see list below)
- Claude identifies an action that could have irreversible consequences
- A task explicitly requests approval-flagged operations
- Financial, communication, or external system actions are needed

### Sensitive Actions Requiring Approval

| Category | Examples |
|----------|----------|
| **Communication** | Sending emails to new contacts, SMS messages, direct messages |
| **Financial** | Payments, transfers, purchases, subscription changes |
| **Social Media** | Posting tweets, LinkedIn updates, Facebook posts, Instagram content |
| **External Systems** | API calls that modify data, database writes, config changes |
| **File Operations** | Deleting files outside temp folders, modifying system files |
| **Code Execution** | Running scripts that affect production, deploying code |
| **Data Export** | Sharing data externally, generating reports for external parties |

## 4. Inputs

| Input | Location | Description |
|-------|----------|-------------|
| Task files | `Needs_Action/*.md` | Tasks requesting sensitive actions |
| Plan files | `Plans/*.md` | Plans with approval-flagged steps |
| Approval templates | `plants/approval_template.md` | Template for approval requests |
| Context | YAML frontmatter | Task metadata, related files, priority |

## 5. Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Approval requests | `Pending_Approval/` | Request files awaiting human decision |
| Approved actions | `Approved/` | Requests that received approval |
| Rejected actions | `Rejected/` | Requests that were denied |
| Audit logs | `Logs/System_Log.md` | Timestamped approval/rejection records |

### Approval Request File Structure

```markdown
---
Type: approval_request
Status: pending_approval
Priority: <priority level>
Created_at: <ISO timestamp>
Source_task: <original task filename>
Action_type: <email/payment/post/etc>
Risk_level: <low/medium/high>
---

# Approval Request: <Action Description>

## Requested Action
(Clear description of what will be done)

## Context
- **Source Task:** `Needs_Action/<task_file>`
- **Related Plan:** `Plans/<plan_file>` (if applicable)
- **Target:** <recipient/system/destination>
- **Timing:** <when the action should occur>

## Why Approval is Required
(Explanation of why this action requires human oversight)

## Risk Assessment
| Factor | Details |
|--------|---------|
| Reversibility | Can this be undone? |
| Impact | Who/what is affected? |
| Sensitivity | Does this involve sensitive data? |

## Proposed Content
(Exact content that will be sent/posted/executed)

---

## Human Decision Required

**To Approve:** Move this file to `Approved/` folder
**To Reject:** Move this file to `Rejected/` folder

## Approval Section (Filled by Human)

- [ ] I have reviewed this request
- [ ] I understand the risks
- [ ] I authorize this action

**Approved by:** ________________
**Date:** ________________
**Notes:** ________________
```

## 6. Approval Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        HUMAN APPROVAL WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │  Task/Plan   │
  │  Identified  │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │  Is Action       │
  │  Sensitive?      │
  └──────┬───────────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │    ┌──────────────┐
    │    │ Proceed      │
    │    │ Normally     │
    │    └──────────────┘
    ▼
  ┌──────────────────────┐
  │ Create Approval      │
  │ Request File         │
  │ (Pending_Approval/)  │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │  HUMAN REVIEW        │
  │  (Wait for decision) │
  └──────────┬───────────┘
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
  ┌─────────┐ ┌──────────┐
  │ APPROVE │ │ REJECT   │
  └────┬────┘ └────┬─────┘
       │           │
       │ Human     │ Human
       │ moves to  │ moves to
       │ Approved/ │ Rejected/
       │           │
       ▼           ▼
  ┌─────────┐ ┌──────────┐
  │ Execute │ │ Stop &   │
  │ Action  │ │ Log      │
  └────┬────┘ └──────────┘
       │
       ▼
  ┌─────────┐
  │ Move to │
  │ Done/   │
  └─────────┘
```

### Workflow Steps

1. **Detection** — Claude identifies a sensitive action in task/plan
2. **Pause** — Claude stops and does NOT execute the action
3. **Request Creation** — Generate approval request file in `Pending_Approval/`
4. **Notification** — Log the pending approval, optionally alert user
5. **Wait** — Claude waits for human to move the file
6. **Decision Check** — Periodically check folder status:
   - File in `Approved/` → Execute action, log, move to Done
   - File in `Rejected/` → Stop, log rejection, notify
   - File in `Pending_Approval/` → Continue waiting

## 7. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **Never bypass approval** | Sensitive actions are NEVER executed without approval file movement |
| **No auto-approval** | Claude does not move files on behalf of humans |
| **Complete context** | Approval requests must include full context and risk assessment |
| **Exact content** | Proposed content must be exact (no "similar" or "approximate") |
| **Audit trail** | All approvals/rejections logged to `Logs/System_Log.md` |
| **One action per request** | Each approval request covers exactly one sensitive action |
| **No pressure tactics** | Requests must not urge or pressure humans to approve |
| **Clear rejection path** | Rejection must be as easy as approval |

### Claude Limitations

```
┌─────────────────────────────────────────────────────────────┐
│  What Claude CANNOT do in this workflow:                    │
├─────────────────────────────────────────────────────────────┤
│  ✗ Execute sensitive actions without approval               │
│  ✗ Move files between approval folders                      │
│  ✗ Assume approval after timeout                            │
│  ✗ Modify approval requests after creation                  │
│  ✗ Send partial or modified content                         │
│  ✗ Bypass the workflow for "urgent" requests                │
└─────────────────────────────────────────────────────────────┘
```

## 8. Human Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **Review requests** | Regularly check `Pending_Approval/` for new requests |
| **Understand context** | Read the full request including risks and proposed content |
| **Make informed decisions** | Approve only when confident in the action |
| **Add notes** | Document reasoning in approval section when needed |
| **Move files** | Physically move files to `Approved/` or `Rejected/` |
| **Monitor logs** | Review `Logs/System_Log.md` for approval history |

### Human Checklist for Approval

- [ ] I understand what action will be taken
- [ ] I have reviewed the proposed content
- [ ] I understand the risks involved
- [ ] I know how to contact support if something goes wrong
- [ ] I am authorized to approve this type of action

## 9. Example Flow

### Example 1: Email to New Contact

```
┌─────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│ Needs_Action/   │ ──→ │ Pending_Approval/   │ ──→ │    Approved/      │
│                 │     │                     │     │                   │
│ task_email.md   │     │ approval_email_*.md │     │ approval_email_*.md│
│                 │     │                     │     │                   │
│ "Send intro     │     │ Human reviews:      │     │ Claude executes:  │
│  email to       │     │ - Recipient         │     │ - Sends email     │
│  new client"    │     │ - Email content     │     │ - Logs action     │
│                 │     │ - Risk assessment   │     │ - Moves to Done/  │
└─────────────────┘     └─────────────────────┘     └───────────────────┘
         │                       │                           │
         │                       │                           ▼
         │                       │                    ┌──────────────┐
         │                       │                    │    Done/     │
         │                       │                    │              │
         │                       │                    │ task_email.md│
         │                       │                    │ (completed)  │
         │                       │                    └──────────────┘
         │                       │
         │                       └───────┐
         │                               │
         │                        ┌──────────────┐
         │                        │   Rejected/  │
         │                        │              │
         │                        │ (Alternative │
         │                        │  outcome)    │
         │                        └──────────────┘
         │                               │
         │                               ▼
         │                        Claude stops
         │                        Logs rejection
         │                        Notifies user
         │
         ▼
  Task identified
  requires approval
```

### Step-by-Step Example

1. **Task created:** `Needs_Action/task_send_client_email.md`
   - Description: "Send introduction email to new client john@example.com"
   - Action type: Email to new contact (SENSITIVE)

2. **Claude detects sensitive action:**
   - Email to new contact → Requires approval
   - Stops execution immediately

3. **Claude creates approval request:** `Pending_Approval/approval_email_john_1708185600.md`
   ```markdown
   ---
   Type: approval_request
   Status: pending_approval
   Action_type: email
   Risk_level: medium
   Source_task: task_send_client_email.md
   ---
   # Approval Request: Send Email to john@example.com

   ## Requested Action
   Send introduction email to new client contact.

   ## Proposed Content
   Subject: Introduction from [Company]
   Body: [Full email text displayed here]

   ## Why Approval Required
   This is a new external contact. Email content must be verified.
   ```

4. **Human reviews:**
   - Opens file in Obsidian
   - Reads proposed content
   - Verifies recipient and message

5. **Human approves:**
   - Fills in approval section
   - Moves file to `Approved/` folder

6. **Claude detects approval:**
   - Periodic check finds file in `Approved/`
   - Executes email send action
   - Logs to `System_Log.md`
   - Moves original task to `Done/`

7. **Alternative: Human rejects:**
   - Moves file to `Rejected/`
   - Adds rejection note
   - Claude stops, logs rejection
   - Task remains in `Needs_Action/` for revision

---

## Folder Structure

```
hackathon-0/
├── Needs_Action/        # Pending tasks
├── Pending_Approval/    # Awaiting human decision (CREATED BY WORKFLOW)
├── Approved/            # Approved actions ready for execution
├── Rejected/            # Denied actions (stopped)
├── Done/                # Completed tasks
├── Logs/
│   └── System_Log.md    # Approval/rejection audit trail
└── plants/
    └── approval_template.md
```

## Related Files

- `Vault_Watcher_Skill.md` — Creates tasks from Inbox files
- `Task_Planner_Skill.md` — Generates plans for tasks
- `process_tasks.py` — Processes completed tasks
- `Company_Handbook.md` — Company rules and guidelines
- `Logs/System_Log.md` — Audit trail for all actions
