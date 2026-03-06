#!/bin/bash
# ============================================================
# Platinum Tier - Start All Services
# ============================================================
# Ubuntu/Debian startup script for AI Employee system
# Starts all core services with auto-restart on crash
#
# Usage:
#   ./start_all.sh start     - Start all services
#   ./start_all.sh stop      - Stop all services
#   ./start_all.sh restart   - Restart all services
#   ./start_all.sh status    - Show service status
#   ./start_all.sh logs      - Show all logs
# ============================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/Logs/central"
PID_DIR="$SCRIPT_DIR/.pids"
VENV_DIR="$SCRIPT_DIR/venv"

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Python command (use venv if available)
if [ -d "$VENV_DIR" ]; then
    PYTHON="$VENV_DIR/bin/python"
else
    PYTHON="python3"
fi

# Service definitions
declare -A SERVICES
SERVICES=(
    ["file_watcher"]="file_watcher.py"
    ["process_tasks"]="process_tasks.py"
    ["ralph_loop"]="skills/ralph_loop.py"
    ["health_monitor"]="platinum/health_monitor.py"
    ["gmail_mcp"]="mcp_servers/gmail_mcp/server.py"
    ["linkedin_mcp"]="mcp_servers/linkedin_mcp/server.py"
    ["odoo_mcp"]="mcp_servers/odoo_mcp/server.py"
    ["twitter_mcp"]="mcp_servers/social_mcp/twitter_server.py"
    ["facebook_mcp"]="mcp_servers/social_mcp/facebook_server.py"
    ["instagram_mcp"]="mcp_servers/social_mcp/instagram_server.py"
)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Start a service
start_service() {
    local name=$1
    local script=$2
    local log_file="$LOG_DIR/${name}.log"
    local pid_file="$PID_DIR/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "$name is already running (PID: $pid)"
            return 0
        fi
        rm -f "$pid_file"
    fi

    log_info "Starting $name..."
    
    # Start in background with auto-restart logic
    nohup bash -c "
        while true; do
            $PYTHON $script >> $log_file 2>&1
            echo \"\$(date '+%Y-%m-%d %H:%M:%S') - $name crashed, restarting...\" >> $log_file
            sleep 2
        done
    " > /dev/null 2>&1 &
    
    local pid=$!
    echo $pid > "$pid_file"
    
    sleep 1
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "$name started (PID: $pid)"
        return 0
    else
        log_error "Failed to start $name"
        rm -f "$pid_file"
        return 1
    fi
}

# Stop a service
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        log_warn "$name is not running (no PID file)"
        return 0
    fi

    local pid=$(cat "$pid_file")
    
    if ps -p "$pid" > /dev/null 2>&1; then
        log_info "Stopping $name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        kill -9 "$pid" 2>/dev/null || true
        log_info "$name stopped"
    else
        log_warn "$name was not running"
    fi
    
    rm -f "$pid_file"
}

# Get service status
get_status() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo "stopped"
        return
    fi

    local pid=$(cat "$pid_file")
    
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "running:$pid"
    else
        echo "crashed"
    fi
}

# Start all services
start_all() {
    log_info "Starting all AI Employee services..."
    
    # Start MCP servers first
    for name in gmail_mcp linkedin_mcp odoo_mcp twitter_mcp facebook_mcp instagram_mcp; do
        if [ -f "$SCRIPT_DIR/${SERVICES[$name]}" ]; then
            start_service "$name" "${SERVICES[$name]}"
        else
            log_warn "Script not found for $name: ${SERVICES[$name]}"
        fi
    done
    
    sleep 3  # Wait for MCP servers to initialize
    
    # Start core services
    for name in file_watcher process_tasks ralph_loop health_monitor; do
        if [ -f "$SCRIPT_DIR/${SERVICES[$name]}" ]; then
            start_service "$name" "${SERVICES[$name]}"
        else
            log_warn "Script not found for $name: ${SERVICES[$name]}"
        fi
    done
    
    log_info "All services started!"
}

# Stop all services
stop_all() {
    log_info "Stopping all AI Employee services..."
    
    # Stop in reverse order
    for name in health_monitor ralph_loop process_tasks file_watcher instagram_mcp facebook_mcp twitter_mcp odoo_mcp linkedin_mcp gmail_mcp; do
        stop_service "$name"
    done
    
    log_info "All services stopped!"
}

# Show status
show_status() {
    echo ""
    echo "============================================================"
    echo "           AI Employee Service Status"
    echo "============================================================"
    echo ""
    
    printf "%-20s %-15s %-10s\n" "SERVICE" "STATUS" "PID"
    echo "------------------------------------------------------------"
    
    for name in "${!SERVICES[@]}"; do
        local status=$(get_status "$name")
        local state=$(echo "$status" | cut -d: -f1)
        local pid=$(echo "$status" | cut -d: -f2)
        
        if [ "$state" = "running" ]; then
            printf "%-20s ${GREEN}%-15s${NC} %-10s\n" "$name" "$state" "$pid"
        elif [ "$state" = "crashed" ]; then
            printf "%-20s ${RED}%-15s${NC} %-10s\n" "$name" "$state" "N/A"
        else
            printf "%-20s ${YELLOW}%-15s${NC} %-10s\n" "$name" "$state" "N/A"
        fi
    done
    
    echo ""
    echo "============================================================"
}

# Show logs
show_logs() {
    local service=$1
    
    if [ -n "$service" ]; then
        local log_file="$LOG_DIR/${service}.log"
        if [ -f "$log_file" ]; then
            tail -f "$log_file"
        else
            log_error "Log file not found: $log_file"
        fi
    else
        # Show all logs in separate tabs (or sequentially)
        log_info "Showing last 50 lines of all logs..."
        for log_file in "$LOG_DIR"/*.log; do
            if [ -f "$log_file" ]; then
                echo ""
                echo "=== $(basename "$log_file") ==="
                tail -50 "$log_file"
            fi
        done
    fi
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    
    # Create virtual environment if not exists
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate and install
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
    
    log_info "Dependencies installed!"
}

# Setup cron jobs
setup_cron() {
    log_info "Setting up cron jobs..."
    
    # Add sync cron job (every 2 minutes)
    (crontab -l 2>/dev/null | grep -v "sync.sh"; echo "*/2 * * * * $SCRIPT_DIR/scripts/sync.sh pull >> $LOG_DIR/sync.log 2>&1") | crontab -
    
    log_info "Cron jobs configured!"
}

# Main command handler
case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    install)
        install_deps
        ;;
    cron)
        setup_cron
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|install|cron}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  status   - Show service status"
        echo "  logs     - Show logs (optionally specify service)"
        echo "  install  - Install dependencies"
        echo "  cron     - Setup cron jobs"
        exit 1
        ;;
esac

exit 0
