# ============================================================
# Platinum Tier - Quick Reference Card
# ============================================================

# START ALL SERVICES
./start_all.sh start

# CHECK STATUS
./start_all.sh status
pm2 status

# VIEW LOGS
./start_all.sh logs
pm2 logs

# STOP SERVICES
./start_all.sh stop
pm2 stop ecosystem.config.js

# RESTART SERVICES
./start_all.sh restart
pm2 restart ecosystem.config.js

# ============================================================
# VAULT SYNC
# ============================================================

# Initialize (one-time)
./scripts/sync.sh init

# Manual sync
./scripts/sync.sh pull    # Cloud → Local
./scripts/sync.sh push    # Local → Cloud

# Check status
./scripts/sync.sh status

# Cron setup (Cloud - every 2 min)
*/2 * * * * /path/to/scripts/sync.sh pull

# ============================================================
# HEALTH MONITOR
# ============================================================

# Run directly
python3 platinum/health_monitor.py &

# Or via PM2
pm2 start ecosystem.config.js --only health_monitor

# View health logs
tail -f Logs/central/health_monitor.log

# ============================================================
# SOCIAL MEDIA MCP SERVERS
# ============================================================

# Twitter (Port 8004)
curl -X POST http://127.0.0.1:8004/post_tweet \
  -H "Content-Type: application/json" \
  -d '{"message": "Test tweet", "requires_approval": true}'

# Facebook (Port 8005)
curl -X POST http://127.0.0.1:8005/post_facebook \
  -H "Content-Type: application/json" \
  -d '{"message": "Test post", "requires_approval": true}'

# Instagram (Port 8006)
curl -X POST http://127.0.0.1:8006/post_instagram \
  -H "Content-Type: application/json" \
  -d '{"message": "Test post", "requires_approval": true}'

# ============================================================
# WORK-ZONE SPECIALIZATION
# ============================================================

from platinum.work_zone import get_cloud_agent, get_local_agent

# Cloud Agent (Draft Mode)
cloud = get_cloud_agent()
cloud.claim_task("task.md", "Needs_Action")
cloud.create_draft_email("task.md", "Draft content")
cloud.submit_for_approval("task.md", "send_email")

# Local Agent (Final Actions)
local = get_local_agent()
local.process_approval("approval.md", approved=True)
local.finalize_send("draft.md")

# ============================================================
# MCP SERVER PORTS
# ============================================================
# Gmail:      8001
# LinkedIn:   8002
# Odoo ERP:   8003
# Twitter:    8004
# Facebook:   8005
# Instagram:  8006

# ============================================================
# FOLDER STRUCTURE
# ============================================================
# AI_Employee_Vault/Vault/           - Cloud workspace
# AI_Employee_Vault/Needs_Action/    - Unclaimed tasks
# AI_Employee_Vault/Pending_Approval/- Awaiting approval
# AI_Employee_Vault/In_Progress/     - Local workspace
# AI_Employee_Vault/Updates/         - Alerts and status

# ============================================================
# SECURITY RULES
# ============================================================
# Cloud NEVER stores:
# - .env files
# - API tokens
# - WhatsApp sessions
# - Payment credentials

# Only sync:
# - Markdown files
# - State files
# - NO secrets

# ============================================================
# UBUNTU PRODUCTION SETUP
# ============================================================
# 1. Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nodejs npm
sudo npm install -g pm2

# 2. Setup project
cd /path/to/bronze
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Make scripts executable
chmod +x start_all.sh scripts/sync.sh

# 4. Start with PM2
pm2 start ecosystem.config.js
pm2 startup
pm2 save

# 5. Setup cron for sync
crontab -e
# Add: */2 * * * * /path/to/scripts/sync.sh pull
