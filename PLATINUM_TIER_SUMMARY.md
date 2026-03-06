# Platinum Tier - Production-Ready AI Employee System

## Overview

Platinum Tier upgrades the Gold Tier system to production-grade with:
- **24/7 Cloud Deployment** - Always-on autonomous operation
- **Cloud + Local Architecture** - Secure separation of concerns
- **Git-Based Vault Sync** - Bidirectional synchronization
- **Health Monitoring** - Auto-recovery on failures
- **Social Media MCP Agents** - Twitter, Facebook, Instagram
- **Work-Zone Specialization** - Domain ownership with claim-by-move

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PLATINUM TIER ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐         ┌─────────────────────────────┐
│      CLOUD AGENT (VPS)      │         │     LOCAL AGENT (On-Prem)   │
│                             │         │                             │
│  ┌───────────────────────┐  │         │  ┌───────────────────────┐  │
│  │   Email Triage        │  │         │  │   Human Approvals     │  │
│  │   Draft Replies       │  │         │  │   Payments            │  │
│  │   Draft Social Posts  │  │         │  │   Final Send/Post     │  │
│  │   NEVER Send Direct   │  │         │  │   Vault Sync (Pull)   │  │
│  └───────────────────────┘  │         │  └───────────────────────┘  │
│                             │         │                             │
│  Services:                  │         │  Services:                  │
│  - file_watcher.py          │         │  - process_tasks.py         │
│  - ralph_loop.py            │         │  - health_monitor.py        │
│  - Gmail MCP (8001)         │         │  - All MCP Servers          │
│  - LinkedIn MCP (8002)      │         │  - Twitter MCP (8004)       │
│  - Twitter MCP (8004)       │         │  - Facebook MCP (8005)      │
│  - Facebook MCP (8005)      │         │  - Instagram MCP (8006)     │
│  - Instagram MCP (8006)     │         │  - Odoo MCP (8003)          │
│                             │         │                             │
│  Sync: pull every 2 min     │────────▶│  Sync: push on changes      │
└─────────────────────────────┘         └─────────────────────────────┘
              │                                     │
              └─────────────────┬───────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Git Remote (Sync)   │
                    │   - Markdown files    │
                    │   - State files       │
                    │   - NO secrets        │
                    └───────────────────────┘
```

---

## Folder Structure

```
bronze/
├── AI_Employee_Vault/
│   ├── Vault/              # Cloud agent workspace
│   ├── Needs_Action/       # Tasks requiring action
│   ├── Pending_Approval/   # Awaiting human approval
│   ├── In_Progress/        # Currently being worked on
│   ├── Updates/            # Status updates and alerts
│   ├── reports/            # Social media history
│   └── personal/           # Personal tasks
│
├── Inbox/                  # New incoming data
├── Needs_Action/           # Legacy task folder
├── Pending_Approval/       # Legacy approval folder
├── Approved/               # Approved items
├── Done/                   # Completed tasks
├── Plans/                  # AI-generated plans
├── Logs/
│   ├── central/            # Centralized service logs
│   ├── Archive/            # Archived logs
│   └── System_Log.md       # Main system log
│
├── mcp_servers/
│   ├── gmail_mcp/          # Gmail MCP server
│   ├── linkedin_mcp/       # LinkedIn MCP server
│   ├── odoo_mcp/           # Odoo ERP MCP server
│   └── social_mcp/         # Social media MCP servers
│       ├── twitter_server.py
│       ├── facebook_server.py
│       └── instagram_server.py
│
├── platinum/               # Platinum tier modules
│   ├── health_monitor.py   # Service health monitoring
│   └── work_zone.py        # Work-zone specialization
│
├── scripts/                # Utility scripts
│   ├── sync.sh             # Git-based vault sync
│   └── cron_setup.txt      # Cron job configurations
│
├── skills/                 # AI skills/modules
│   ├── ralph_loop.py       # Autonomous execution loop
│   ├── gold_stability.py   # Stability features
│   └── ...
│
├── start_all.sh            # Master startup script
├── ecosystem.config.js     # PM2 process config
├── .gitignore              # Security ignore rules
└── .env                    # Environment variables (NEVER COMMIT)
```

---

## 1. Cloud 24/7 Deployment

### Ubuntu Setup

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nodejs npm

# 2. Install PM2 globally
sudo npm install -g pm2

# 3. Setup virtual environment
cd /path/to/bronze
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Make scripts executable
chmod +x start_all.sh
chmod +x scripts/sync.sh

# 5. Install PM2 services
pm2 start ecosystem.config.js

# 6. Enable PM2 on reboot
pm2 startup
pm2 save
```

### start_all.sh Usage

```bash
# Start all services
./start_all.sh start

# Stop all services
./start_all.sh stop

# Restart all services
./start_all.sh restart

# Check status
./start_all.sh status

# View logs
./start_all.sh logs
./start_all.sh logs file_watcher
```

### PM2 Commands

```bash
# Start services
pm2 start ecosystem.config.js

# Stop services
pm2 stop ecosystem.config.js

# Restart services
pm2 restart ecosystem.config.js

# View status
pm2 status

# View logs
pm2 logs

# Monitor resources
pm2 monit

# Save current process list
pm2 save

# Setup PM2 on boot
pm2 startup
```

---

## 2. Work-Zone Specialization

### Domain Ownership

| Domain | Capabilities | Restrictions |
|--------|--------------|--------------|
| **Cloud** | Email triage, Draft replies, Draft social posts | NEVER send directly |
| **Local** | Human approvals, Payments, Final send/post | Requires human approval |

### Claim-by-Move Rule

```python
from platinum.work_zone import get_cloud_agent, get_local_agent

# Cloud Agent - Draft Mode
cloud = get_cloud_agent()

# Claim a task (moves to Cloud workspace)
success, msg = cloud.claim_task("task_email_001.md", "Needs_Action")

# Create draft email
success, msg = cloud.create_draft_email(
    "task_email_001.md",
    "Draft reply content..."
)

# Submit for approval
success, msg = cloud.submit_for_approval(
    "task_email_001.md",
    "send_email"
)

# Local Agent - Final Actions
local = get_local_agent()

# Process approval
success, msg = local.process_approval("approval_123.md", approved=True)

# Finalize and send
success, msg = local.finalize_send("draft_email_123.md")
```

### Folder Ownership

```
Needs_Action/          # Unclaimed tasks
    │
    ├── claimed by Cloud ──▶ AI_Employee_Vault/Vault/
    │
    └── claimed by Local ──▶ AI_Employee_Vault/In_Progress/
```

---

## 3. Vault Sync (Cloud ↔ Local)

### Git-Based Sync

```bash
# Initialize sync (one-time setup)
./scripts/sync.sh init

# Set remote URL
export VAULT_SYNC_REMOTE_URL="https://github.com/user/ai-vault.git"

# Manual sync
./scripts/sync.sh pull    # Cloud → Local
./scripts/sync.sh push    # Local → Cloud

# Check status
./scripts/sync.sh status
```

### Cron Setup (Cloud)

Add to crontab (`crontab -e`):

```cron
# Vault sync every 2 minutes
*/2 * * * * /path/to/bronze/scripts/sync.sh pull >> /path/to/bronze/Logs/sync.log 2>&1
```

### Sync Rules

| Rule | Implementation |
|------|----------------|
| Prevent merge conflicts | Git merge with `--no-edit` |
| Single writer for Dashboard.md | Cloud-only writes |
| Ignore secrets | `.gitignore` excludes `.env`, `tokens/`, `sessions/`, `*.key` |

### What Syncs

**Synced (Markdown/State):**
- `AI_Employee_Vault/**/*.md`
- `Inbox/**/*.md`
- `Needs_Action/**/*.md`
- `Pending_Approval/**/*.md`
- `Approved/**/*.md`
- `Done/**/*.md`
- `Plans/**/*.md`
- `Dashboard.md`

**NOT Synced (Secrets):**
- `.env`
- `tokens/`
- `sessions/`
- `*.key`
- `credentials.json`

---

## 4. Social Media MCP Agents

### Twitter MCP Server (Port 8004)

```python
import requests

# Post tweet (requires approval)
response = requests.post("http://127.0.0.1:8004/post_tweet", json={
    "message": "Excited to announce our new product! #launch",
    "requires_approval": True
})

# Create draft
response = requests.post("http://127.0.0.1:8004/create_draft", json={
    "message": "Draft tweet content",
    "scheduled_time": "2026-02-27T10:00:00"
})

# Get history
response = requests.post("http://127.0.0.1:8004/get_history", json={
    "limit": 10
})

# Generate summary
response = requests.post("http://127.0.0.1:8004/generate_summary", json={
    "content": "Long content to summarize into a tweet"
})
```

### Facebook MCP Server (Port 8005)

```python
import requests

# Post to Facebook (requires approval)
response = requests.post("http://127.0.0.1:8005/post_facebook", json={
    "message": "Check out our latest update!",
    "link": "https://example.com/blog",
    "requires_approval": True
})

# Create draft
response = requests.post("http://127.0.0.1:8005/create_draft", json={
    "message": "Draft post content",
    "link": "https://example.com"
})
```

### Instagram MCP Server (Port 8006)

```python
import requests

# Post to Instagram (requires approval)
response = requests.post("http://127.0.0.1:8006/post_instagram", json={
    "message": "Behind the scenes! #teamwork",
    "image_url": "https://example.com/image.jpg",
    "requires_approval": True
})

# Generate caption
response = requests.post("http://127.0.0.1:8006/generate_caption", json={
    "content": "Content to convert to caption",
    "style": "casual"  # casual, professional, enthusiastic, tech
})
```

### All Actions Require Approval

```
Draft Created ──▶ Approval Request ──▶ Human Approval ──▶ Post Published
                      │
                      └──▶ Pending_Approval/{approval_id}.md
```

---

## 5. Health Monitoring

### health_monitor.py

Monitors all services and auto-recovers on failure.

```python
# Run as daemon
python3 platinum/health_monitor.py &

# Or via PM2
pm2 start ecosystem.config.js --only health_monitor
```

### Monitored Services

| Service | Port | Auto-Restart |
|---------|------|--------------|
| file_watcher | - | ✓ |
| process_tasks | - | ✓ |
| ralph_loop | - | ✓ |
| gmail_mcp | 8001 | ✓ |
| linkedin_mcp | 8002 | ✓ |
| odoo_mcp | 8003 | ✓ |
| twitter_mcp | 8004 | ✓ |
| facebook_mcp | 8005 | ✓ |
| instagram_mcp | 8006 | ✓ |

### Alert System

When a service fails:
1. Attempt auto-restart (max 5 attempts)
2. Log error to `Logs/central/health_monitor.log`
3. Write alert to `AI_Employee_Vault/Updates/alert_{service}_{timestamp}.md`

---

## 6. Security Rules

### Cloud NEVER Stores

- `.env` files
- API tokens
- WhatsApp sessions
- Payment credentials

### Only Sync

- Markdown files
- State files
- Task files
- Logs (non-sensitive)

### .gitignore Enforcement

```
# Critical security ignores
.env
*.key
tokens/
sessions/
credentials.json
*_secret*
```

---

## Quick Start

### Cloud Agent (VPS)

```bash
# 1. Clone and setup
git clone <repo> /opt/ai-employee
cd /opt/ai-employee
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with cloud credentials

# 3. Initialize sync
./scripts/sync.sh init
export VAULT_SYNC_REMOTE_URL="<your-git-url>"

# 4. Start services
./start_all.sh start

# 5. Setup cron for sync
crontab -e
# Add: */2 * * * * /opt/ai-employee/scripts/sync.sh pull
```

### Local Agent (On-Prem)

```bash
# 1. Clone and setup
git clone <repo> ~/ai-employee
cd ~/ai-employee
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with local credentials

# 3. Initialize sync
./scripts/sync.sh init
export VAULT_SYNC_REMOTE_URL="<your-git-url>"

# 4. Start services with PM2
pm2 start ecosystem.config.js
pm2 startup
pm2 save

# 5. Monitor
pm2 monit
```

---

## Production Checklist

| Item | Status |
|------|--------|
| Ubuntu setup complete | ☐ |
| Python venv created | ☐ |
| Dependencies installed | ☐ |
| .env configured (secrets) | ☐ |
| PM2 installed globally | ☐ |
| ecosystem.config.js configured | ☐ |
| start_all.sh executable | ☐ |
| sync.sh initialized | ☐ |
| Git remote configured | ☐ |
| Cron jobs setup | ☐ |
| Health monitor running | ☐ |
| MCP servers started | ☐ |
| Logs folder writable | ☐ |
| .gitignore in place | ☐ |

---

## Files Created/Updated

### New Files
| File | Purpose |
|------|---------|
| `start_all.sh` | Master startup script |
| `ecosystem.config.js` | PM2 process config |
| `scripts/sync.sh` | Git-based vault sync |
| `scripts/cron_setup.txt` | Cron job templates |
| `platinum/health_monitor.py` | Service health monitoring |
| `platinum/work_zone.py` | Work-zone specialization |
| `mcp_servers/social_mcp/twitter_server.py` | Twitter MCP server |
| `mcp_servers/social_mcp/facebook_server.py` | Facebook MCP server |
| `mcp_servers/social_mcp/instagram_server.py` | Instagram MCP server |
| `.gitignore` | Security ignore rules |
| `PLATINUM_TIER_SUMMARY.md` | This documentation |

### Updated Folders
```
AI_Employee_Vault/
├── Vault/              # NEW - Cloud workspace
├── Needs_Action/       # NEW - Shared task queue
├── Pending_Approval/   # NEW - Approval requests
├── In_Progress/        # NEW - Local workspace
├── Updates/            # NEW - Alerts and status
└── reports/            # Social media history
```

---

## Demo Flow

### 1. Email Triage (Cloud)

```
1. New email arrives
2. file_watcher.py creates task in Needs_Action/
3. Cloud agent claims task (moves to Vault/)
4. Cloud drafts reply
5. Cloud submits for approval
```

### 2. Human Approval (Local)

```
1. Local agent sees approval in Pending_Approval/
2. Human reviews and approves
3. Local agent moves to Approved/
4. Local agent finalizes and sends
5. Task moved to Done/
```

### 3. Social Media Post (Cloud → Local)

```
1. Cloud drafts tweet in Vault/
2. Cloud creates approval request
3. Sync pushes draft to Local
4. Human approves on Local
5. Local posts via Twitter MCP
6. History logged to reports/
```

### 4. Health Recovery

```
1. Service crashes
2. health_monitor.py detects failure
3. Auto-restart attempted
4. If successful: service resumes
5. If failed: alert written to Updates/
```

---

## Summary

**Platinum Tier: PRODUCTION-READY** ✅

| Feature | Implementation |
|---------|----------------|
| 24/7 Cloud Deployment | start_all.sh + PM2 |
| Work-Zone Specialization | Cloud drafts, Local sends |
| Vault Sync | Git-based, every 2 minutes |
| Social Media MCP | Twitter, Facebook, Instagram |
| Health Monitoring | Auto-restart + alerts |
| Security | Secrets never sync |

**System is hackathon-ready and production-deployable.** 🎉
