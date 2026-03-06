---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Vault Watcher Skill

## 1. Skill Name

**Vault_Watcher**

## 2. Purpose

The Vault Watcher monitors the `Inbox` folder for new files and automatically creates actionable task files in the `Needs_Action` folder. This enables a hands-off workflow where dropping a file into Inbox triggers task creation without manual intervention.

**Goal in simple terms:** Watch for new files → Create tasks → Track progress

## 3. Trigger Condition

The watcher activates when:
- A new file is added to the `Inbox/` folder
- The file has not been previously processed (tracked via `filename` in YAML frontmatter)
- The watcher script (`file_watcher.py`) is running

## 4. Inputs

| Input | Location | Description |
|-------|----------|-------------|
| New files | `Inbox/` | Any file dropped into this folder triggers task creation |
| Task template | `plants/task_templete.md` | Template used to generate task files |
| Processed file registry | `Needs_Action/`, `Done/` | Scanned on startup to avoid duplicate tasks |

## 5. Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Task files | `Needs_Action/` | Markdown files with YAML frontmatter containing task metadata |
| Error logs | `Logs/watcher_errors.log` | Timestamped error entries for failed operations |
| Console output | Terminal | Real-time status messages during watcher execution |

### Task File Structure

```markdown
---
Type: general_task
Status: pending
Priority: medium
Created_at: <ISO timestamp>
Related_files: ['Inbox/<original_filename>']
filename: <original_filename>
---
# Task: Review File '<original_filename>'
## Description
A new file '<original_filename>' was added to the Inbox and requires review.
## Checklist
- [ ] step 1
- [ ] step 2
- [ ] step 3
## Notes
(Add any reasoning or context here)
```

## 6. Processing Steps

1. **Initialize**
   - Create required directories (`Inbox/`, `Needs_Action/`, `Logs/`) if missing
   - Build set of already-processed filenames by scanning `Needs_Action/` and `Done/`

2. **Monitor Loop** (runs every 5 seconds)
   - List all files in `Inbox/`
   - For each file:
     - Check if filename exists in processed set → skip if true
     - Verify it's a file (not a directory)
     - Generate unique task filename: `task_<original>_<timestamp>.md`
     - Load template from `plants/task_templete.md`
     - Populate template with dynamic values (timestamp, filename, description)
     - Write task file to `Needs_Action/`
     - Add filename to processed set

3. **Error Handling**
   - Template not found → log error, wait 60 seconds, retry
   - Unexpected errors → log to `Logs/watcher_errors.log`, continue monitoring

## 7. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **No duplicate tasks** | Filename tracked in processed set; checked before creation |
| **No overwrite existing tasks** | Unique timestamp in task filename prevents collision |
| **One task per file** | Each Inbox file creates exactly one task in Needs_Action |
| **Log all errors** | Errors written to `Logs/watcher_errors.log` with ISO timestamp |
| **Graceful shutdown** | Ctrl+C stops watcher cleanly with exit message |
| **Non-destructive** | Original Inbox files remain untouched |

## 8. Example Flow

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────┐
│   Inbox/    │ ──→ │  Needs_Action/   │ ──→ │   process    │ ──→ │   Done/  │
│             │     │                  │     │   task.py    │     │          │
│ notes.txt   │     │ task_notes_123.md│     │              │     │ task_*.md│
│ (new file)  │     │ (pending task)   │     │              │     │ (done)   │
└─────────────┘     └──────────────────┘     └──────────────┘     └──────────┘
       │                    │                        │                  │
       │                    │                        │                  │
       ▼                    ▼                        ▼                  ▼
  File dropped        Task created              Status updated      Archived
  by user             by watcher                & Dashboard         with log
                                                updated
```

### Step-by-Step Example

1. **User action:** Drop `meeting_notes.txt` into `Inbox/`
2. **Watcher detects:** New file found (not in processed set)
3. **Task created:** `Needs_Action/task_meeting_notes_1708185600.md`
   - Status: `pending`
   - Related_files: `['Inbox/meeting_notes.txt']`
   - filename: `meeting_notes.txt`
4. **User/Agent processes:** Opens task, completes checklist items
5. **Process task runs:** 
   - Status changed to `completed`
   - File moved to `Done/`
   - `Dashboard.md` updated
   - `System_Log.md` appended

---

## Related Files

- `file_watcher.py` — Main watcher implementation
- `process_task.py` — Task processor (moves tasks to Done)
- `plants/task_templete.md` — Task file template
- `Dashboard.md` — Task overview dashboard
- `System_Log.md` — Activity log
