# 🤖 Personal AI Employee (Digital FTE)

> **Hackathon Project: Bronze → Silver Level Upgrade**
> A fully autonomous digital employee that monitors emails, messages, files, and finances — processes tasks through AI reasoning, and requires human approval for sensitive actions.

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN ENTRY (main.py)                      │
├─────────────────────────────────────────────────────────────────┤
│                        ORCHESTRATOR                              │
│              Claude Reasoning Cycle: Read → Plan →              │
│              Write → Execute                                     │
├──────┬──────┬──────┬──────────┬──────────┬──────────────────────┤
│Gmail │WhatsApp│File  │Finance   │Ralph   │Approval             │
│Watcher│Watcher │Watcher│Watcher  │Loop    │System (HITL)        │
├──────┴──────┴──────┴──────────┴──────────┴──────────────────────┤
│                        MCP ACTION LAYER                          │
│           Gmail MCP │ WhatsApp MCP │ LinkedIn MCP                │
├─────────────────────────────────────────────────────────────────┤
│                    SCHEDULER + WATCHDOG                          │
│              (Auto-restart + Periodic Tasks)                     │
├─────────────────────────────────────────────────────────────────┤
│                    OBSIDIAN DASHBOARD                            │
│              (DASHBOARD.md — auto-updating)                     │
├─────────────────────────────────────────────────────────────────┤
│                    LOGGING + AUDIT                               │
│         system.log │ audit.jsonl │ task/*.log                    │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Final Folder Structure

```
bronze/
├── main.py                          # System entry point
├── orchestrator.py                  # Main brain loop (Claude reasoning cycle)
├── config.py                        # Central configuration
├── logger_setup.py                  # Logging & audit system
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
│
├── scripts/
│   ├── __init__.py
│   ├── gmail_watcher.py             # Gmail inbox monitor
│   ├── whatsapp_watcher.py          # WhatsApp Web monitor
│   ├── filesystem_watcher.py        # OS file system monitor
│   ├── finance_watcher.py           # Financial transaction monitor
│   ├── ralph_loop.py                # Persistent task completion (re-injection)
│   ├── plan_generator.py            # Claude reasoning output handler
│   ├── approval_system.py           # Human-in-the-loop approval
│   ├── dashboard_generator.py       # Obsidian dashboard.md creator
│   ├── scheduler.py                 # Cron/loop scheduling
│   └── watchdog.py                  # Auto-restart process manager
│
├── mcp_servers/
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   └── auth.py                  # Shared authentication utilities
│   ├── gmail_mcp/
│   │   ├── __init__.py
│   │   └── server.py                # Gmail MCP server (read/send/search)
│   ├── whatsapp_mcp/
│   │   ├── __init__.py
│   │   └── server.py                # WhatsApp MCP server (send/read/search)
│   └── linkedin_mcp/
│       ├── __init__.py
│       └── server.py                # LinkedIn MCP (search/message/post)
│
├── AI_Employee_Vault/
│   ├── Inbox/                       # New tasks from watchers
│   ├── Needs_Action/                # Failed/re-injected tasks
│   ├── Plans/                       # Generated execution plans
│   ├── Pending_Approval/            # Tasks awaiting human review
│   ├── Approved/                    # Approved tasks ready to execute
│   ├── Rejected/                    # Rejected tasks
│   ├── Done/                        # Completed tasks
│   ├── Review_Required/             # Manual review queue
│   └── Logs/                        # Vault-specific logs
│
├── Logs/
│   ├── system.log                   # Main system log (rotating)
│   ├── audit.jsonl                  # Structured audit trail
│   └── tasks/                       # Per-task log files
│
├── .pids/                           # Process ID files
├── whatsapp_session/                # WhatsApp Web Chrome session
├── linkedin_session/                # LinkedIn Chrome session
└── dashboard_ui/                    # Web dashboard (future)
```

## 🚀 Quick Start

### 1. Setup (First Time Only)

```bash
# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Copy and configure environment
copy .env.example .env
# Edit .env and add your API keys
```

### 2. Configure API Keys

Edit `.env` file with your credentials:

```env
# For Gmail watching
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
GMAIL_CREDENTIALS_PATH=credentials.json  # Download from Google Cloud Console

# For AI reasoning (at least one required)
ANTHROPIC_API_KEY=your_claude_key
# OR
OPENAI_API_KEY=your_openai_key
```

### 3. Run System Diagnostics

```bash
python main.py test
```

This checks all modules, folders, and configuration.

### 4. Start the System

```bash
python main.py start
```

The system will:
- ✅ Start all 4 watchers (Gmail, WhatsApp, File, Finance)
- ✅ Launch the orchestrator (main brain loop)
- ✅ Start Ralph Loop (auto-retry system)
- ✅ Start Watchdog (auto-restart manager)
- ✅ Start Scheduler (periodic tasks)
- ✅ Generate initial DASHBOARD.md

### 5. Monitor

```bash
# View system status
python main.py status

# View live dashboard (open in Obsidian)
AI_Employee_Vault/DASHBOARD.md

# List pending approvals
python main.py list-pending
```

### 6. Approve/Reject Tasks

```bash
# Approve a task
python main.py approve GMAIL_ABC123

# Reject with reason
python main.py reject GMAIL_ABC123 --reason "Not urgent"
```

### 7. Stop the System

```bash
python main.py stop
# Or press Ctrl+C
```

## 🔄 Task Flow

```
[Watcher detects event]
        ↓
    [Inbox/] ← New task created
        ↓
[Orchestrator picks up]
        ↓
  ┌── READ ──→ Analyze task content
  │     ↓
  ├── PLAN ──→ Generate action steps
  │     ↓
  ├── WRITE ──→ Save plan to Plans/
  │     ↓
  ├── APPROVAL CHECK ──→ Needs human review?
  │     ├─ YES → [Pending_Approval/] → Wait for human → [Approved/] or [Rejected/]
  │     └─ NO  ↓
  └── EXECUTE ──→ Run via MCP layer
        ↓
   Success? ──→ YES → [Done/]
        └─ NO  → [Needs_Action/] → Ralph Loop retries (up to 10x)
                                      ↓
                                 Still fails? → [Needs_Action/] ESCALATED → Human
```

## 🧠 Ralph Wiggum Loop

The system **NEVER gives up** on a task:

1. Task fails → retry counter increments
2. Task re-injected into `Needs_Action/` with error context
3. Orchestrator picks it up again
4. Repeats up to `RALPH_LOOP_MAX_RETRIES` (default: 10)
5. If still failing → **ESCALATED** to human with full error history

## 🔒 Security Rules

| Rule | Implementation |
|------|---------------|
| No hardcoded secrets | All secrets in `.env`, loaded via `python-dotenv` |
| Approval for payments | `finance_watcher` always requires approval |
| Approval for new contacts | `send_message_to_new_contact` requires approval |
| Approval for social posts | `post_update` requires approval |
| Audit trail | Every action logged to `audit.jsonl` |
| Session isolation | Browser sessions stored in dedicated profiles |

## 📊 MCP Tools Available

### Gmail MCP
- `read_emails` — Fetch recent emails
- `send_email` — Send emails (requires approval for new contacts)
- `search_emails` — Gmail query search
- `get_email_by_id` — Full email content
- `mark_as_read` — Mark as read
- `delete_email` — Trash email

### WhatsApp MCP
- `send_message` — Message existing contact
- `send_message_to_new_contact` — Message new contact (requires approval)
- `read_messages` — Read chat history
- `get_contacts` — List visible contacts
- `search_chats` — Search conversations

### LinkedIn MCP
- `search_people` — Find people by keywords
- `send_connection_request` — Connect (requires approval)
- `send_message` — Message connections
- `get_profile` — View profile info
- `post_update` — Post to feed (requires approval)

## 🛠️ Individual Components

Run any component standalone:

```bash
# Gmail watcher only
python scripts/gmail_watcher.py

# Ralph loop only
python scripts/ralph_loop.py

# Approval system CLI
python scripts/approval_system.py list
python scripts/approval_system.py approve TASK_ID

# Dashboard update once
python scripts/dashboard_generator.py once

# Watchdog process manager
python scripts/watchdog.py status
python scripts/watchdog.py start
```

## 🐛 Troubleshooting

### Gmail Watcher not working
1. Download `credentials.json` from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API in your Google Cloud project
3. Set `GMAIL_CREDENTIALS_PATH` in `.env`
4. First run will open browser for OAuth authorization

### WhatsApp session expired
1. Delete `whatsapp_session/` folder
2. Restart system — it will show QR code
3. Scan QR code with WhatsApp on your phone
4. Session persists across restarts

### "No AI API key configured"
- Add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` to `.env`
- System works without AI — uses heuristic fallback plans

### Process keeps restarting
- Check `Logs/system.log` for error details
- Use `python main.py status` to see which processes are failing
- Use `python scripts/watchdog.py status` for detailed process status

## 📋 Hackathon Checklist

- [x] Watchers (Gmail, WhatsApp, File, Finance)
- [x] Orchestrator with Claude reasoning loop
- [x] MCP action layer integration
- [x] Human-in-the-loop approval system
- [x] Obsidian dashboard system
- [x] Logging and audit system
- [x] Scheduling system (cron/loop)
- [x] Watchdog process manager
- [x] Ralph Wiggum loop (never give up)
- [x] Security (no hardcoded secrets, approval gates)
- [x] Production-ready folder structure

## 📄 License

Hackathon project — educational purposes.
