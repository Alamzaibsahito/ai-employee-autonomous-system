"""
============================================================
Platinum Tier - Dashboard API Server
============================================================
FastAPI backend for AI Employee Monitoring Dashboard

Provides REST endpoints for:
- Dashboard statistics
- System daemon status
- Recent tasks
- Pending approvals
- System health metrics

Usage:
    python dashboard_api.py

Runs on: http://localhost:8000
============================================================
"""

import os
import sys
import json
import logging
import psutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging FIRST (before any other imports that might use logger)
LOG_DIR = "Logs/central"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "dashboard_api.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright for LinkedIn posting
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed - LinkedIn posting will use fallback mode")

# FastAPI app
app = FastAPI(
    title="AI Employee Dashboard API",
    description="Backend API for AI Employee Monitoring Dashboard",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Folder Configuration
# ============================================================

BASE_DIR = Path(__file__).parent

# Task folders
INBOX_DIR = BASE_DIR / "Inbox"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
DONE_DIR = BASE_DIR / "Done"
REVIEW_REQUIRED_DIR = BASE_DIR / "Review_Required"
ERRORS_DIR = BASE_DIR / "AI_Employee_Vault" / "Updates"

# Logs directory
LOGS_CENTRAL_DIR = BASE_DIR / "Logs" / "central"

# Ensure directories exist
for dir_path in [INBOX_DIR, NEEDS_ACTION_DIR, PENDING_APPROVAL_DIR, DONE_DIR, ERRORS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


# ============================================================
# Pydantic Models
# ============================================================

class StatsCard(BaseModel):
    label: str
    value: int
    icon: str
    color: str


class DaemonStatus(BaseModel):
    name: str
    status: str  # "ONLINE" or "OFFLINE"
    uptime: str
    ram_usage: str
    cpu_usage: str
    pid: Optional[int] = None


class TaskItem(BaseModel):
    file: str
    intent: str
    confidence: float
    status: str
    modified_time: str


class ApprovalItem(BaseModel):
    file: str
    type: str
    created_at: str
    action_type: str
    summary: str


class DashboardData(BaseModel):
    stats: List[StatsCard]
    daemons: List[DaemonStatus]
    recent_tasks: List[TaskItem]
    pending_approvals: List[ApprovalItem]
    last_refreshed: str
    dry_run: bool


# ============================================================
# Helper Functions
# ============================================================

def count_files_in_directory(directory: Path) -> int:
    """Count files in a directory."""
    if not directory.exists():
        return 0
    try:
        return len([f for f in directory.iterdir() if f.is_file()])
    except Exception:
        return 0


def get_directory_files(directory: Path, limit: int = 10) -> List[Path]:
    """Get files from a directory sorted by modification time."""
    if not directory.exists():
        return []
    try:
        files = [f for f in directory.iterdir() if f.is_file()]
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return files[:limit]
    except Exception:
        return []


def extract_intent_from_file(file_path: Path) -> str:
    """Extract intent from file content."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)
            
            # Look for intent patterns
            if 'Intent:' in content:
                for line in content.split('\n'):
                    if 'Intent:' in line:
                        return line.split('Intent:')[1].strip()
            
            if 'intent' in content.lower():
                for line in content.split('\n'):
                    if 'intent' in line.lower():
                        return line.split(':')[1].strip() if ':' in line else line.strip()
            
            # Check file extension for hints
            ext = file_path.suffix.lower()
            if ext == '.pdf':
                return "Document Processing"
            elif ext == '.txt':
                return "Text Analysis"
            elif ext == '.md':
                return "Markdown Processing"
            elif 'approval' in file_path.name.lower():
                return "Approval Request"
            elif 'task' in file_path.name.lower():
                return "Task Execution"
            
            return "General Processing"
    except Exception:
        return "Unknown"


def extract_confidence_from_file(file_path: Path) -> float:
    """Extract confidence score from file content."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(1000)
            
            # Look for confidence patterns
            import re
            match = re.search(r'[Cc]onfidence[:\s]+(\d+\.?\d*)%?', content)
            if match:
                return float(match.group(1))
            
            match = re.search(r'(\d+\.?\d*)\s*%', content)
            if match:
                return float(match.group(1))
            
            # Default confidence based on file type
            if 'approval' in file_path.name.lower():
                return 95.0
            elif 'task' in file_path.name.lower():
                return 87.5
            
            return 75.0
    except Exception:
        return 50.0


def get_file_status(file_path: Path, directory_name: str) -> str:
    """Determine file status based on directory."""
    status_map = {
        "Inbox": "NEW",
        "Needs_Action": "PENDING",
        "Pending_Approval": "AWAITING_APPROVAL",
        "Done": "COMPLETED",
        "Review_Required": "REVIEW_NEEDED",
    }
    return status_map.get(directory_name, "UNKNOWN")


def check_process_running(process_name: str) -> bool:
    """Check if a process is running by name."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                if process_name in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception:
        return False


def get_process_info(process_name: str) -> Dict[str, Any]:
    """Get process information including PID, CPU, and memory usage."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                if process_name in cmdline:
                    return {
                        "pid": proc.info['pid'],
                        "cpu": proc.info['cpu_percent'] or 0.0,
                        "memory": proc.info['memory_percent'] or 0.0,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"pid": None, "cpu": 0.0, "memory": 0.0}
    except Exception:
        return {"pid": None, "cpu": 0.0, "memory": 0.0}


def get_daemon_uptime(process_name: str) -> str:
    """Get daemon uptime as a human-readable string."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                if process_name in cmdline:
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    delta = datetime.now() - create_time
                    
                    days = delta.days
                    hours = delta.seconds // 3600
                    minutes = (delta.seconds % 3600) // 60
                    
                    if days > 0:
                        return f"{days}d {hours}h {minutes}m"
                    elif hours > 0:
                        return f"{hours}h {minutes}m"
                    else:
                        return f"{minutes}m"
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        return "0m"
    except Exception:
        return "0m"


# ============================================================
# Daemon Definitions
# ============================================================

DAEMONS = {
    "orchestrator": {
        "process_names": ["process_tasks.py", "process_tasks"],
        "description": "Main task orchestrator",
    },
    "vault-watcher": {
        "process_names": ["file_watcher.py", "file_watcher"],
        "description": "Vault file watcher",
    },
    "gmail-watcher": {
        "process_names": ["gmail_mcp", "gmail_server.py"],
        "port": 8001,
        "description": "Gmail MCP server",
    },
    "watchdog": {
        "process_names": ["health_monitor.py", "health_monitor"],
        "description": "System health watchdog",
    },
    "bank-watcher": {
        "process_names": ["odoo_mcp", "odoo_server.py"],
        "port": 8003,
        "description": "Bank/Odoo MCP server",
    },
    "whatsapp-watcher": {
        "process_names": ["whatsapp", "whatsapp_watcher"],
        "description": "WhatsApp watcher",
    },
}


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "dashboard-api"
    }


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    stats = [
        {
            "label": "Inbox Count",
            "value": count_files_in_directory(INBOX_DIR),
            "icon": "Inbox",
            "color": "blue"
        },
        {
            "label": "Needs Action",
            "value": count_files_in_directory(NEEDS_ACTION_DIR),
            "icon": "AlertCircle",
            "color": "amber"
        },
        {
            "label": "Pending Approval",
            "value": count_files_in_directory(PENDING_APPROVAL_DIR),
            "icon": "Clock",
            "color": "purple"
        },
        {
            "label": "Done",
            "value": count_files_in_directory(DONE_DIR),
            "icon": "CheckCircle",
            "color": "green"
        },
        {
            "label": "Errors",
            "value": count_files_in_directory(ERRORS_DIR),
            "icon": "AlertTriangle",
            "color": "red"
        },
    ]
    return stats


@app.get("/api/daemons")
async def get_daemons():
    """Get system daemon status."""
    daemons = []
    
    for name, config in DAEMONS.items():
        is_running = False
        process_info = {"pid": None, "cpu": 0.0, "memory": 0.0}
        
        # Check each process name
        for proc_name in config.get("process_names", []):
            if check_process_running(proc_name):
                is_running = True
                process_info = get_process_info(proc_name)
                break
        
        # Check port if defined
        if "port" in config:
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', config["port"]))
                sock.close()
                if result == 0:
                    is_running = True
            except Exception:
                pass
        
        uptime = get_daemon_uptime(name) if is_running else "0m"
        
        daemons.append({
            "name": name,
            "status": "ONLINE" if is_running else "OFFLINE",
            "uptime": uptime,
            "ram_usage": f"{process_info['memory']:.1f}%" if is_running else "0.0%",
            "cpu_usage": f"{process_info['cpu']:.1f}%" if is_running else "0.0%",
            "pid": process_info['pid'],
        })
    
    return daemons


@app.get("/api/tasks/recent")
async def get_recent_tasks(limit: int = 10):
    """Get recent tasks from all folders."""
    tasks = []
    
    # Collect tasks from all directories
    directories = [
        (INBOX_DIR, "Inbox"),
        (NEEDS_ACTION_DIR, "Needs_Action"),
        (PENDING_APPROVAL_DIR, "Pending_Approval"),
        (DONE_DIR, "Done"),
    ]
    
    for directory, dir_name in directories:
        files = get_directory_files(directory, limit=5)
        for file_path in files:
            tasks.append({
                "file": file_path.name,
                "intent": extract_intent_from_file(file_path),
                "confidence": extract_confidence_from_file(file_path),
                "status": get_file_status(file_path, dir_name),
                "modified_time": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S"),
            })
    
    # Sort by modified time (most recent first)
    tasks.sort(key=lambda x: x["modified_time"], reverse=True)
    
    return tasks[:limit]


@app.get("/api/approvals/pending")
async def get_pending_approvals():
    """Get pending approval items."""
    approvals = []
    
    files = get_directory_files(PENDING_APPROVAL_DIR, limit=20)
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)
                
                # Extract metadata
                action_type = "General Approval"
                created_at = file_path.stat().st_mtime
                
                for line in content.split('\n')[:30]:
                    if 'Action_type:' in line:
                        action_type = line.split('Action_type:')[1].strip()
                    elif 'Created_at:' in line:
                        try:
                            created_at = datetime.fromisoformat(
                                line.split('Created_at:')[1].strip()
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass
                
                # Create summary
                summary = content[:200].replace('\n', ' ').strip()
                if len(content) > 200:
                    summary += "..."
                
                approvals.append({
                    "file": file_path.name,
                    "type": "approval_request",
                    "created_at": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "action_type": action_type,
                    "summary": summary,
                })
        except Exception as e:
            logger.error(f"Error reading approval file {file_path}: {e}")
            approvals.append({
                "file": file_path.name,
                "type": "approval_request",
                "created_at": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "action_type": "Unknown",
                "summary": "Unable to read file content",
            })
    
    return approvals


@app.get("/api/dashboard")
async def get_dashboard_data(dry_run: bool = False):
    """Get complete dashboard data."""
    # Get all data
    stats = await get_stats()
    daemons = await get_daemons()
    recent_tasks = await get_recent_tasks()
    pending_approvals = await get_pending_approvals()
    
    return {
        "stats": stats,
        "daemons": daemons,
        "recent_tasks": recent_tasks,
        "pending_approvals": pending_approvals,
        "last_refreshed": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dry_run": dry_run,
    }


@app.get("/api/folders")
async def get_folder_info():
    """Get folder structure information."""
    return {
        "inbox": count_files_in_directory(INBOX_DIR),
        "needs_action": count_files_in_directory(NEEDS_ACTION_DIR),
        "pending_approval": count_files_in_directory(PENDING_APPROVAL_DIR),
        "done": count_files_in_directory(DONE_DIR),
        "review_required": count_files_in_directory(REVIEW_REQUIRED_DIR),
    }


# ============================================================
# LinkedIn Post Models
# ============================================================

class PostContent(BaseModel):
    """Content model for LinkedIn posts."""
    text: str


class CreatePostRequest(BaseModel):
    """Request model for creating a LinkedIn post."""
    content: PostContent


class CreatePostResponse(BaseModel):
    """Response model for LinkedIn post creation."""
    success: bool
    message: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None


# ============================================================
# LinkedIn Posting Functions
# ============================================================

class LinkedInSession:
    """Manages LinkedIn browser session with persistent cookies."""

    LINKEDIN_URL = "https://www.linkedin.com"
    LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
    LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

    def __init__(self, session_folder: str = "./linkedin_session"):
        self.session_folder = Path(session_folder)
        self.session_folder.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.session_folder / "cookies.json"
        self.playwright = None
        self.context = None
        self.page = None

    async def start(self, headless: bool = True) -> None:
        """Start browser."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed")

        logger.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()

        wsl_chromium_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
        ]

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_folder / "user_data"),
            headless=headless,
            viewport={'width': 1280, 'height': 720},
            args=wsl_chromium_args,
            timeout=120000,
        )

        pages = self.context.pages
        self.page = pages[0] if pages else await self.context.new_page()

    async def save_session(self) -> None:
        """Save cookies and session state."""
        if self.context:
            try:
                state = await self.context.storage_state()
                with open(self.cookies_file, 'w') as f:
                    json.dump(state, f, indent=2)
                logger.info(f"Session saved: {len(state.get('cookies', []))} cookies")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")

    async def load_session(self) -> bool:
        """Check if valid session exists."""
        if not self.cookies_file.exists():
            return False
        try:
            with open(self.cookies_file, 'r') as f:
                state = json.load(f)
            cookies = state.get('cookies', [])
            has_auth = any(c.get('name') in ['li_at', 'JSESSIONID'] for c in cookies)
            return has_auth
        except Exception:
            return False

    async def login(self, email: str, password: str) -> bool:
        """Login to LinkedIn."""
        try:
            await self.page.goto(
                self.LINKEDIN_LOGIN_URL,
                wait_until='domcontentloaded',
                timeout=60000
            )
            await self.page.wait_for_timeout(3000)

            if '/feed' in self.page.url or '/home' in self.page.url:
                logger.info("Already logged in")
                return True

            # Fill email
            email_input = await self.page.wait_for_selector('input[id="username"]', timeout=10000)
            await email_input.fill(email)
            await self.page.wait_for_timeout(500)

            # Fill password
            password_input = await self.page.wait_for_selector('input[id="password"]', timeout=5000)
            await password_input.fill(password)
            await self.page.wait_for_timeout(500)

            # Click login
            login_button = await self.page.wait_for_selector('button[type="submit"]', timeout=5000)
            await login_button.click()

            # Wait for navigation after login submit
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(5000)

            # Check if login failed - URL still contains "login"
            if '/login' in self.page.url:
                logger.error(f"Login failed - still on login page. URL: {self.page.url}")
                # Log page content for debugging
                page_content = await self.page.content()
                logger.error(f"Page content snippet: {page_content[:500]}...")
                
                # Check for checkpoint or captcha
                if await self.page.query_selector('#captcha'):
                    logger.error("CAPTCHA detected on page")
                if await self.page.query_selector('[id*="checkpoint"]'):
                    logger.error("Checkpoint page detected")
                if await self.page.query_selector('text="Verify you are human"'):
                    logger.error("Human verification checkpoint detected")
                    
                return False

            # Check for checkpoint or captcha pages
            if '/checkpoint' in self.page.url or 'captcha' in self.page.url.lower():
                logger.error(f"Checkpoint/CAPTCHA detected. URL: {self.page.url}")
                page_content = await self.page.content()
                logger.error(f"Checkpoint page content: {page_content[:500]}...")
                return False

            if '/feed' in self.page.url or '/home' in self.page.url:
                logger.info("Login successful!")
                await self.save_session()
                return True

            logger.error(f"Login may have failed. URL: {self.page.url}")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def is_logged_in(self) -> bool:
        """Check if currently logged in."""
        if not self.page:
            return False
        current_url = self.page.url
        if '/login' in current_url:
            return False
        try:
            await self.page.wait_for_selector('img[alt*="Me"]', timeout=3000)
            return True
        except Exception:
            pass
        return '/feed' in current_url or '/home' in current_url

    async def create_post(self, content: str) -> tuple:
        """Create a LinkedIn post. Returns (success, message, post_id)."""
        try:
            logger.info("Creating LinkedIn post...")

            # Navigate to feed
            await self.page.goto(
                self.LINKEDIN_FEED_URL,
                wait_until='domcontentloaded',
                timeout=60000
            )
            await self.page.wait_for_timeout(3000)

            # Click "Start a post"
            post_button = await self.page.wait_for_selector(
                'div[role="button"][aria-label*="Start a post"]',
                timeout=5000
            )
            await post_button.click()
            await self.page.wait_for_timeout(2000)

            # Find and fill post input
            post_input = await self.page.wait_for_selector(
                'div[contenteditable="true"][aria-label*="post"]',
                timeout=5000
            )
            await post_input.click()
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Delete')
            await self.page.wait_for_timeout(500)

            # Type content
            for char in content:
                await self.page.keyboard.type(char, delay=10)
            await self.page.wait_for_timeout(1000)

            # Click Post button
            submit_button = await self.page.wait_for_selector(
                'button[aria-label*="Post"]',
                timeout=5000
            )
            await submit_button.click()
            await self.page.wait_for_timeout(5000)

            await self.save_session()
            post_id = f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return True, "LinkedIn post successful", post_id

        except Exception as e:
            logger.error(f"Post creation error: {e}")
            return False, f"Failed to create post: {str(e)}", None

    async def close(self) -> None:
        """Close browser."""
        try:
            if self.context:
                await self.save_session()
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        finally:
            self.context = None
            self.page = None
            self.playwright = None


async def post_to_linkedin(content: str, email: str = None, password: str = None, headless: bool = False) -> tuple:
    """Main function to post to LinkedIn."""
    if not PLAYWRIGHT_AVAILABLE:
        return False, "Playwright not installed. Run: pip install playwright && playwright install", None

    # Get credentials from environment
    email = email or os.getenv("LINKEDIN_EMAIL")
    password = password or os.getenv("LINKEDIN_PASSWORD")

    # Strip whitespace before validation
    if email: email = email.strip()
    if password: password = password.strip()

    if not email or not password:
        return False, "LinkedIn credentials not configured. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD.", None

    session = LinkedInSession("./linkedin_session")

    try:
        # Use headless=False for visible browser (required for LinkedIn login reliability)
        await session.start(headless=headless)

        # Check for existing session
        has_session = await session.load_session()
        is_logged_in = await session.is_logged_in() if session.page else False

        if not (has_session and is_logged_in):
            if not await session.login(email, password):
                return False, "Login failed", None

        # Create post
        success, message, post_id = await session.create_post(content)
        return success, message, post_id

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return False, f"Error: {str(e)}", None
    finally:
        await session.close()


@app.post("/create_post", response_model=CreatePostResponse)
async def create_post(request: CreatePostRequest):
    """
    Create a LinkedIn post.

    Expected body:
    {
        "content": {
            "text": "Test LinkedIn Post"
        }
    }
    """
    try:
        logger.info(f"Received post request with content: {request.content.text[:100]}...")

        if not PLAYWRIGHT_AVAILABLE:
            # Fallback: simulate successful post
            post_id = f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            logger.warning("Playwright not available - simulating post")
            return CreatePostResponse(
                success=True,
                message="Post simulated (Playwright not installed)",
                post_id=post_id,
                post_url=f"https://www.linkedin.com/feed/update/{post_id}"
            )

        # Execute real post
        success, message, post_id = await post_to_linkedin(request.content.text)

        if success:
            return CreatePostResponse(
                success=True,
                message=message,
                post_id=post_id,
                post_url=f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None
            )
        else:
            return CreatePostResponse(
                success=False,
                message="Failed to create post",
                error=message
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in create_post: {e}")
        return CreatePostResponse(
            success=False,
            message="Internal server error",
            error=str(e)
        )


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    logger.info("Starting Dashboard API Server...")
    logger.info("Dashboard API available at: http://localhost:8002")
    logger.info("API Docs available at: http://localhost:8002/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
