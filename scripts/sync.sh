#!/bin/bash
# ============================================================
# Platinum Tier - Vault Sync Script
# ============================================================
# Git-based synchronization between Cloud and Local agents
#
# Features:
# - Prevents merge conflicts
# - Single writer for Dashboard.md
# - Ignores secrets (.env, tokens, sessions, *.key)
# - Bidirectional sync (pull/push)
#
# Usage:
#   ./sync.sh pull     - Pull changes from cloud (Cloud → Local)
#   ./sync.sh push     - Push changes to cloud (Local → Cloud)
#   ./sync.sh status   - Show sync status
#   ./sync.sh init     - Initialize git repo for sync
#
# Cron setup (every 2 minutes on cloud):
#   */2 * * * * /path/to/sync.sh pull >> /path/to/Logs/sync.log 2>&1
# ============================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_DIR="$SCRIPT_DIR"
LOG_FILE="$SCRIPT_DIR/Logs/sync.log"
REMOTE_NAME="cloud"
REMOTE_URL="${VAULT_SYNC_REMOTE_URL:-}"
BRANCH_NAME="${VAULT_SYNC_BRANCH:-main}"

# Folders to sync (markdown/state files only)
SYNC_FOLDERS=(
    "AI_Employee_Vault"
    "Inbox"
    "Needs_Action"
    "Pending_Approval"
    "Approved"
    "Done"
    "Plans"
    "Logs"
    "Accounting"
)

# Files to always ignore (secrets)
IGNORE_FILES=(
    ".env"
    "*.key"
    "tokens/*"
    "sessions/*"
    "*.pem"
    "*.crt"
    "*_secret*"
    "*_password*"
    "credentials.json"
    "token.json"
)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [INFO] $1" >> "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [WARN] $1" >> "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [ERROR] $1" >> "$LOG_FILE"
}

log_sync() {
    echo -e "${BLUE}[SYNC]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [SYNC] $1" >> "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Initialize git repository for sync
init_git() {
    log_info "Initializing git repository for sync..."
    
    cd "$GIT_DIR"
    
    # Check if already initialized
    if [ -d ".git" ]; then
        log_warn "Git repository already initialized"
        return 0
    fi
    
    # Initialize git repo
    git init
    
    # Create .gitignore for secrets
    cat > .gitignore << 'EOF'
# ============================================================
# Secrets - NEVER sync these
# ============================================================
.env
*.env
.env.*
*.key
*.pem
*.crt
tokens/
sessions/
credentials.json
token.json
*_secret*
*_password*
*.secret

# ============================================================
# Python
# ============================================================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env/
*.egg-info/
dist/
build/

# ============================================================
# IDE
# ============================================================
.idea/
.vscode/
*.swp
*.swo
*~

# ============================================================
# OS
# ============================================================
.DS_Store
Thumbs.db

# ============================================================
# Logs (keep recent, archive old)
# ============================================================
Logs/Archive/
Logs/central/*.log.*

# ============================================================
# Temporary
# ============================================================
tmp/
temp/
*.tmp
.pids/
EOF

    log_info "Created .gitignore for secrets"
    
    # Initial commit
    git add .
    git commit -m "Initial commit - AI Employee Vault" || true
    
    log_info "Git repository initialized"
    echo ""
    echo "Next steps:"
    echo "1. Set remote URL: git remote add cloud <REMOTE_URL>"
    echo "2. Or set environment variable: export VAULT_SYNC_REMOTE_URL=<REMOTE_URL>"
    echo "3. Run: ./sync.sh push"
}

# Configure git safe settings
configure_git_safe() {
    cd "$GIT_DIR"
    
    # Prevent merge conflicts - use ours for Dashboard.md
    git config merge.ours.driver true
    
    # Set safe merge strategy
    git config pull.rebase false
    
    # Configure line endings
    git config core.autocrlf input
}

# Check if git is initialized
check_git_initialized() {
    if [ ! -d ".git" ]; then
        log_error "Git repository not initialized. Run: ./sync.sh init"
        return 1
    fi
    return 0
}

# Check if remote is configured
check_remote_configured() {
    if [ -z "$REMOTE_URL" ] && ! git remote get-url "$REMOTE_NAME" > /dev/null 2>&1; then
        log_error "Remote not configured. Set VAULT_SYNC_REMOTE_URL or run: git remote add cloud <URL>"
        return 1
    fi
    return 0
}

# Pull changes from cloud (Cloud → Local)
pull_changes() {
    log_sync "Starting pull from cloud..."
    
    cd "$GIT_DIR"
    
    check_git_initialized || return 1
    
    # Set remote if URL provided
    if [ -n "$REMOTE_URL" ]; then
        git remote get-url "$REMOTE_NAME" > /dev/null 2>&1 || git remote add "$REMOTE_NAME" "$REMOTE_URL"
    fi
    
    check_remote_configured || return 1
    
    # Fetch latest changes
    git fetch "$REMOTE_NAME"
    
    # Check for conflicts before merging
    if ! git merge-tree $(git merge-base "$BRANCH_NAME" "$REMOTE_NAME/$BRANCH_NAME") "$BRANCH_NAME" "$REMOTE_NAME/$BRANCH_NAME" | grep -q "^<<<<<<<"; then
        # No conflicts - proceed with merge
        git pull "$REMOTE_NAME" "$BRANCH_NAME" --no-edit || {
            log_warn "Pull had conflicts, accepting cloud version for Dashboard.md"
            # Accept cloud version for Dashboard.md specifically
            git checkout --ours "Dashboard.md" 2>/dev/null || true
            git add "Dashboard.md" 2>/dev/null || true
            git commit -m "Sync: Resolved Dashboard.md conflict" || true
        }
        log_sync "Pull completed successfully"
    else
        log_warn "Merge conflicts detected, handling gracefully..."
        # Accept incoming changes for most files
        git merge "$REMOTE_NAME/$BRANCH_NAME" -X theirs --no-edit || {
            # If still conflicts, abort and log
            git merge --abort
            log_error "Merge failed, conflicts need manual resolution"
            return 1
        }
        log_sync "Pull completed with conflict resolution"
    fi
    
    log_info "Pull from cloud completed"
}

# Push changes to cloud (Local → Cloud)
push_changes() {
    log_sync "Starting push to cloud..."
    
    cd "$GIT_DIR"
    
    check_git_initialized || return 1
    
    # Set remote if URL provided
    if [ -n "$REMOTE_URL" ]; then
        git remote get-url "$REMOTE_NAME" > /dev/null 2>&1 || git remote add "$REMOTE_NAME" "$REMOTE_URL"
    fi
    
    check_remote_configured || return 1
    
    # Stage changes
    git add -A
    
    # Check if there are changes to commit
    if git diff --cached --quiet; then
        log_info "No changes to push"
        return 0
    fi
    
    # Commit with timestamp
    git commit -m "Sync: Local changes $(date '+%Y-%m-%d %H:%M:%S')" || {
        log_warn "Nothing to commit or commit failed"
    }
    
    # Push to remote
    git push "$REMOTE_NAME" "$BRANCH_NAME" || {
        log_error "Push failed, pulling latest and retrying..."
        git pull "$REMOTE_NAME" "$BRANCH_NAME" --no-edit || true
        git push "$REMOTE_NAME" "$BRANCH_NAME" || {
            log_error "Push failed after pull, changes may need manual merge"
            return 1
        }
    }
    
    log_sync "Push to cloud completed"
}

# Show sync status
show_status() {
    cd "$GIT_DIR"
    
    check_git_initialized || return 1
    
    echo ""
    echo "============================================================"
    echo "           Vault Sync Status"
    echo "============================================================"
    echo ""
    
    # Git status
    echo "Git Status:"
    git status --short || true
    echo ""
    
    # Remote info
    echo "Remote Configuration:"
    if git remote get-url "$REMOTE_NAME" > /dev/null 2>&1; then
        echo "  $REMOTE_NAME: $(git remote get-url "$REMOTE_NAME")"
    else
        echo "  $REMOTE_NAME: Not configured"
    fi
    echo ""
    
    # Branch info
    echo "Branch:"
    git branch -a | grep "^*" || true
    echo ""
    
    # Last sync time
    if [ -f "$LOG_FILE" ]; then
        echo "Last Sync Activity:"
        tail -5 "$LOG_FILE"
    fi
    echo ""
    
    echo "============================================================"
}

# Main command handler
case "${1:-}" in
    pull)
        pull_changes
        ;;
    push)
        push_changes
        ;;
    status)
        show_status
        ;;
    init)
        init_git
        configure_git_safe
        ;;
    *)
        echo "Usage: $0 {pull|push|status|init}"
        echo ""
        echo "Commands:"
        echo "  pull   - Pull changes from cloud (Cloud → Local)"
        echo "  push   - Push changes to cloud (Local → Cloud)"
        echo "  status - Show sync status"
        echo "  init   - Initialize git repository for sync"
        echo ""
        echo "Environment Variables:"
        echo "  VAULT_SYNC_REMOTE_URL - Git remote URL for cloud sync"
        echo "  VAULT_SYNC_BRANCH     - Branch name (default: main)"
        echo ""
        echo "Cron Setup (Cloud - every 2 minutes):"
        echo "  */2 * * * * /path/to/sync.sh pull >> /path/to/Logs/sync.log 2>&1"
        exit 1
        ;;
esac

exit 0
