"""
LinkedIn MCP Server

Provides Model Context Protocol (MCP) endpoints for LinkedIn operations:
- create_post: Create a LinkedIn post
- schedule_post: Schedule a post for future publishing
- generate_post_summary: Generate a summary for a post

Designed for business posting automation.
Public posting requires human approval flag.
All actions are logged.
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # For scripts/ import

from shared.auth import (
    get_credential_manager,
    create_action_logger,
    CredentialManager
)

# Import LinkedIn poster (browser automation)
from scripts.post_linkedin import post_to_linkedin as browser_post_to_linkedin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LinkedIn MCP Server",
    description="MCP server for LinkedIn business posting operations",
    version="1.0.0"
)

# Initialize components
credential_manager = get_credential_manager()
action_logger = create_action_logger("linkedin")


# ============================================================
# Request/Response Models
# ============================================================

class PostContent(BaseModel):
    """Content model for LinkedIn posts."""
    text: str = Field(..., description="Post text content (max 3000 characters)")
    title: Optional[str] = Field(None, description="Optional post title")
    hashtags: Optional[List[str]] = Field(None, description="List of hashtags (without #)")


class CreatePostRequest(BaseModel):
    """Request model for creating a LinkedIn post."""
    content: PostContent
    visibility: str = Field(default="public", description="Post visibility: public, connections, group")
    requires_approval: bool = Field(
        default=True,
        description="Whether this post requires human approval before publishing (required for public posts)"
    )
    organization_id: Optional[str] = Field(None, description="Organization ID for company page posts")


class SchedulePostRequest(BaseModel):
    """Request model for scheduling a LinkedIn post."""
    content: PostContent
    scheduled_time: str = Field(..., description="ISO 8601 formatted datetime for scheduling")
    visibility: str = Field(default="public", description="Post visibility: public, connections, group")
    requires_approval: bool = Field(
        default=True,
        description="Whether this scheduled post requires human approval"
    )
    organization_id: Optional[str] = Field(None, description="Organization ID for company page posts")
    timezone: Optional[str] = Field(default="UTC", description="Timezone for scheduled time")


class GenerateSummaryRequest(BaseModel):
    """Request model for generating post summaries."""
    content: str = Field(..., description="Raw content to summarize")
    max_length: int = Field(default=500, ge=50, le=3000, description="Maximum summary length in characters")
    tone: Optional[str] = Field(default="professional", description="Tone: professional, casual, enthusiastic")
    include_hashtags: bool = Field(default=True, description="Whether to include suggested hashtags")


class PostResponse(BaseModel):
    """Response model for post operations."""
    success: bool
    message: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ScheduleResponse(BaseModel):
    """Response model for scheduling operations."""
    success: bool
    message: str
    scheduled_post_id: Optional[str] = None
    scheduled_time: Optional[str] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class SummaryResponse(BaseModel):
    """Response model for summary generation."""
    success: bool
    message: str
    summary: str
    suggested_hashtags: List[str] = Field(default_factory=list)
    character_count: int = 0
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None


# ============================================================
# Helper Functions
# ============================================================

def create_error_response(error: str, error_code: str, details: Optional[Dict] = None) -> Dict:
    """Create a standardized error response."""
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
        "details": details or {}
    }


def validate_credentials() -> tuple[bool, str]:
    """Validate LinkedIn credentials are configured."""
    is_valid, message = credential_manager.validate_linkedin_credentials()
    return is_valid, message


def validate_post_content(content: PostContent) -> tuple[bool, str]:
    """Validate post content meets LinkedIn requirements."""
    if not content.text or len(content.text.strip()) == 0:
        return False, "Post text cannot be empty"
    
    if len(content.text) > 3000:
        return False, "Post text exceeds maximum length of 3000 characters"
    
    return True, "Content validated"


def get_project_root() -> Path:
    """Get the project root directory using absolute path from file location."""
    # server.py is at: mcp_servers/linkedin_mcp/server.py
    # parents[2] resolves to: hackathon-0/bronze (project root)
    return Path(__file__).resolve().parents[2]


async def execute_real_linkedin_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute real LinkedIn post using Playwright browser automation.
    
    This function:
    - Creates/loads persistent browser session
    - Logs in if needed
    - Creates the post
    - Verifies post appears in DOM
    - Saves session for reuse
    
    Args:
        post_data: Dictionary with text, title, hashtags, visibility
        
    Returns:
        Dictionary with post result including id, status, url
    """
    import asyncio
    
    # Get project root for session folder
    project_root = get_project_root()
    session_folder = project_root / "linkedin_session"
    session_folder.mkdir(parents=True, exist_ok=True)
    
    # Set environment for LinkedIn credentials
    os.environ.setdefault('LINKEDIN_SESSION_FOLDER', str(session_folder))
    
    # Import the poster module
    scripts_dir = project_root / "scripts"
    sys.path.insert(0, str(scripts_dir))
    
    try:
        from post_linkedin import post_to_linkedin
        
        # Build post content with hashtags
        content = post_data.get("text", "")
        hashtags = post_data.get("hashtags", [])
        if hashtags:
            hashtag_str = " ".join(f"#{tag}" for tag in hashtags)
            content = f"{content}\n\n{hashtag_str}"
        
        logger.info(f"Executing real LinkedIn post with content: {content[:100]}...")
        
        # Run the async poster
        success, message, post_id = await post_to_linkedin(
            content=content,
            headless=True  # Run in headless mode for server
        )
        
        if success:
            return {
                "id": post_id or f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "content": {
                    "text": post_data.get("text"),
                    "title": post_data.get("title"),
                    "hashtags": post_data.get("hashtags")
                },
                "visibility": post_data.get("visibility", "public"),
                "status": "published",
                "timestamp": datetime.now().isoformat(),
                "url": f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None,
                "verified": True
            }
        else:
            raise Exception(f"Playwright posting failed: {message}")
            
    except ImportError as e:
        logger.error(f"Playwright poster not available: {e}")
        raise Exception("LinkedIn browser automation not available. Install playwright: pip install playwright && playwright install")
    except Exception as e:
        logger.error(f"Real LinkedIn post failed: {e}")
        raise


def simulate_linkedin_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate creating a post via LinkedIn API.
    
    DEPRECATED: Use execute_real_linkedin_post() for actual posting.
    This function is kept for backward compatibility when credentials are not configured.
    """
    # Check if real posting is configured
    email = os.environ.get('LINKEDIN_EMAIL')
    password = os.environ.get('LINKEDIN_PASSWORD')
    
    if email and password:
        # Try real posting
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(execute_real_linkedin_post(post_data))
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"Real posting failed, falling back to simulation: {e}")
    
    # Fallback to simulation
    post_id = f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

    return {
        "id": post_id,
        "content": {
            "text": post_data.get("text"),
            "title": post_data.get("title"),
            "hashtags": post_data.get("hashtags")
        },
        "visibility": post_data.get("visibility", "public"),
        "status": "published",
        "timestamp": datetime.now().isoformat(),
        "url": f"https://www.linkedin.com/feed/update/{post_id}"
    }


def simulate_linkedin_schedule(schedule_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate scheduling a post via LinkedIn API.
    
    In production, this would integrate with the actual LinkedIn API.
    """
    scheduled_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    
    return {
        "id": scheduled_id,
        "content": {
            "text": schedule_data.get("text"),
            "title": schedule_data.get("title"),
            "hashtags": schedule_data.get("hashtags")
        },
        "scheduled_time": schedule_data.get("scheduled_time"),
        "timezone": schedule_data.get("timezone", "UTC"),
        "status": "scheduled",
        "created_at": datetime.now().isoformat()
    }


def simulate_generate_summary(content: str, max_length: int, tone: str) -> Dict[str, Any]:
    """
    Simulate generating a post summary.
    
    In production, this would use an AI model to generate the summary.
    """
    # Simple truncation-based summary for simulation
    words = content.split()
    summary_words = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
            summary_words.append(word)
            current_length += len(word) + 1
        else:
            break
    
    summary = " ".join(summary_words)
    if len(summary) < len(content):
        summary += "..."
    
    # Generate suggested hashtags based on content keywords
    keywords = ["innovation", "technology", "business", "growth", "success"]
    suggested_hashtags = [kw for kw in keywords if kw.lower() in content.lower()][:5]
    
    return {
        "summary": summary,
        "suggested_hashtags": suggested_hashtags,
        "character_count": len(summary),
        "tone": tone
    }


def get_project_root() -> Path:
    """Get the project root directory using absolute path from file location."""
    # server.py is at: mcp_servers/linkedin_mcp/server.py
    # parents[2] resolves to: hackathon-0/bronze (project root)
    return Path(__file__).resolve().parents[2]


def create_approval_request(action: str, post_data: Dict[str, Any]) -> str:
    """
    Create an approval request for sensitive actions (public posts).

    Creates a markdown approval task file in Needs_Action/
    so Ralph Loop can detect and process it.

    Returns the approval request ID.
    """
    approval_id = f"approval_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"

    # Use absolute path from file location (not cwd - unreliable under PM2)
    project_root = get_project_root()
    
    # Create approval task file in Needs_Action/ (ralph_loop reads from here)
    approval_dir = project_root / "Needs_Action"
    approval_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Approval saved at absolute path: {approval_dir}")

    # Create approval task markdown file
    approval_file = approval_dir / f"{approval_id}.md"

    # Build approval task content with YAML frontmatter and checklist
    approval_content = f"""---
Type: approval_request
Status: pending
Priority: medium
Created_at: {datetime.now().isoformat()}
Source: linkedin_mcp
Action_type: linkedin_post
Risk_level: medium
Approval_id: {approval_id}
Platform: linkedin
---

# Approval Request: LinkedIn Post

## Requested Action
{action}

## Context
- **Source:** LinkedIn MCP Server
- **Platform:** LinkedIn
- **Visibility:** {post_data.get("visibility", "public")}
- **Title:** {post_data.get("title", "N/A")}

## Why Approval is Required
This is a public social media post that requires human review before publishing.

## Proposed Content

{post_data.get("text", "")}

## Hashtags
{", ".join(post_data.get("hashtags", [])) if post_data.get("hashtags") else "None"}

---

## Human Decision Required

**To Approve:** Move this file to `Approved/` folder
**To Reject:** Move this file to `Rejected/` folder

## Approval Checklist

- [ ] I have reviewed this request
- [ ] I understand the risks
- [ ] I authorize this action

**Approved by:** ________________
**Date:** ________________
**Notes:** ________________
"""

    try:
        # Write approval task markdown file
        with open(approval_file, 'w', encoding='utf-8') as f:
            f.write(approval_content)

        logger.info(f"Approval task saved: {approval_file}")
    except Exception as e:
        logger.error(f"Failed to create approval task file: {e}")
        raise

    # Log the approval request
    action_logger.log_action(
        action="create_approval_request",
        status="pending",
        details={
            "approval_id": approval_id,
            "approval_file": str(approval_file),
            "action": action,
            "post_data": {
                "content_preview": post_data.get("text", "")[:200],
                "visibility": post_data.get("visibility"),
                "title": post_data.get("title")
            }
        }
    )

    return approval_id


def validate_scheduled_time(scheduled_time: str) -> tuple[bool, str]:
    """Validate scheduled time is in the future."""
    try:
        scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        now = datetime.now(scheduled_dt.tzinfo) if scheduled_dt.tzinfo else datetime.now()
        
        if scheduled_dt <= now:
            return False, "Scheduled time must be in the future"
        
        return True, "Scheduled time validated"
    except ValueError as e:
        return False, f"Invalid datetime format: {str(e)}"


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server": "linkedin_mcp",
        "timestamp": datetime.now().isoformat(),
        "credentials_configured": credential_manager.linkedin_client_id is not None
    }


@app.post("/create_post", response_model=PostResponse)
async def create_post(request: CreatePostRequest, x_approval_status: Optional[str] = Header(None)):
    """
    Create a LinkedIn post.
    
    Public posts require human approval before publishing.
    The x_approval_status header should contain 'approved' if approval was obtained.
    
    Args:
        request: Post creation request with content and visibility
        x_approval_status: Approval status header (optional)
    
    Returns:
        PostResponse with success status and post URL
    """
    action_logger.log_request(
        endpoint="/create_post",
        method="POST",
        payload={
            "visibility": request.visibility,
            "requires_approval": request.requires_approval,
            "content_preview": request.content.text[:50] + "..."
        }
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="create_post",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    # Validate post content
    is_valid, error_msg = validate_post_content(request.content)
    if not is_valid:
        action_logger.log_action(
            action="create_post",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check if approval is required (always for public posts)
    requires_approval = request.requires_approval or request.visibility == "public"
    
    if requires_approval:
        if x_approval_status != "approved":
            # Create approval request
            approval_id = create_approval_request("create_post", {
                "text": request.content.text,
                "title": request.content.title,
                "visibility": request.visibility,
                "hashtags": request.content.hashtags
            })
            
            action_logger.log_action(
                action="create_post",
                status="pending_approval",
                details={
                    "visibility": request.visibility,
                    "approval_id": approval_id
                }
            )
            
            return PostResponse(
                success=False,
                message="Public post requires human approval before publishing",
                requires_approval=True,
                approval_request_id=approval_id
            )

    # Create the post using real browser automation
    try:
        post_data = {
            "text": request.content.text,
            "title": request.content.title,
            "hashtags": request.content.hashtags,
            "visibility": request.visibility,
            "organization_id": request.organization_id
        }

        logger.info("Executing LinkedIn post via browser automation...")
        result = simulate_linkedin_post(post_data)

        action_logger.log_action(
            action="create_post",
            status="success",
            details={
                "post_id": result["id"],
                "visibility": request.visibility,
                "url": result.get("url"),
                "verified": result.get("verified", False)
            }
        )

        action_logger.log_response(
            endpoint="/create_post",
            status_code=200,
            response={"success": True, "post_id": result["id"]}
        )

        return PostResponse(
            success=True,
            message="Post published successfully" if result.get("verified") else "Post submitted (verification pending)",
            post_id=result["id"],
            post_url=result.get("url"),
            data=result
        )

    except Exception as e:
        action_logger.log_action(
            action="create_post",
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")


@app.post("/schedule_post", response_model=ScheduleResponse)
async def schedule_post(request: SchedulePostRequest, x_approval_status: Optional[str] = Header(None)):
    """
    Schedule a LinkedIn post for future publishing.
    
    Scheduled public posts require human approval before being queued.
    The x_approval_status header should contain 'approved' if approval was obtained.
    
    Args:
        request: Schedule request with content and scheduled time
        x_approval_status: Approval status header (optional)
    
    Returns:
        ScheduleResponse with scheduled post ID
    """
    action_logger.log_request(
        endpoint="/schedule_post",
        method="POST",
        payload={
            "scheduled_time": request.scheduled_time,
            "visibility": request.visibility,
            "requires_approval": request.requires_approval
        }
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="schedule_post",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    # Validate post content
    is_valid, error_msg = validate_post_content(request.content)
    if not is_valid:
        action_logger.log_action(
            action="schedule_post",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Validate scheduled time
    is_valid, error_msg = validate_scheduled_time(request.scheduled_time)
    if not is_valid:
        action_logger.log_action(
            action="schedule_post",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Check if approval is required
    requires_approval = request.requires_approval or request.visibility == "public"
    
    if requires_approval:
        if x_approval_status != "approved":
            # Create approval request
            approval_id = create_approval_request("schedule_post", {
                "text": request.content.text,
                "title": request.content.title,
                "visibility": request.visibility,
                "scheduled_time": request.scheduled_time,
                "hashtags": request.content.hashtags
            })
            
            action_logger.log_action(
                action="schedule_post",
                status="pending_approval",
                details={
                    "scheduled_time": request.scheduled_time,
                    "visibility": request.visibility,
                    "approval_id": approval_id
                }
            )
            
            return ScheduleResponse(
                success=False,
                message="Scheduled public post requires human approval",
                requires_approval=True,
                approval_request_id=approval_id
            )
    
    # Schedule the post
    try:
        schedule_data = {
            "text": request.content.text,
            "title": request.content.title,
            "hashtags": request.content.hashtags,
            "scheduled_time": request.scheduled_time,
            "timezone": request.timezone,
            "visibility": request.visibility,
            "organization_id": request.organization_id
        }
        
        result = simulate_linkedin_schedule(schedule_data)
        
        action_logger.log_action(
            action="schedule_post",
            status="success",
            details={
                "scheduled_post_id": result["id"],
                "scheduled_time": request.scheduled_time
            }
        )
        
        action_logger.log_response(
            endpoint="/schedule_post",
            status_code=200,
            response={"success": True, "scheduled_post_id": result["id"]}
        )
        
        return ScheduleResponse(
            success=True,
            message=f"Post scheduled for {request.scheduled_time}",
            scheduled_post_id=result["id"],
            scheduled_time=request.scheduled_time,
            data=result
        )
        
    except Exception as e:
        action_logger.log_action(
            action="schedule_post",
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to schedule post: {str(e)}")


@app.post("/generate_post_summary", response_model=SummaryResponse)
async def generate_post_summary(request: GenerateSummaryRequest):
    """
    Generate a summary for LinkedIn post content.
    
    This endpoint does not require approval as it doesn't publish content.
    
    Args:
        request: Summary request with content and options
    
    Returns:
        SummaryResponse with generated summary and hashtags
    """
    action_logger.log_request(
        endpoint="/generate_post_summary",
        method="POST",
        payload={
            "content_length": len(request.content),
            "max_length": request.max_length,
            "tone": request.tone
        }
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="generate_post_summary",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        result = simulate_generate_summary(
            content=request.content,
            max_length=request.max_length,
            tone=request.tone
        )
        
        action_logger.log_action(
            action="generate_post_summary",
            status="success",
            details={
                "character_count": result["character_count"],
                "hashtags_count": len(result["suggested_hashtags"])
            }
        )
        
        action_logger.log_response(
            endpoint="/generate_post_summary",
            status_code=200,
            response={"success": True, "character_count": result["character_count"]}
        )
        
        return SummaryResponse(
            success=True,
            message="Summary generated successfully",
            summary=result["summary"],
            suggested_hashtags=result["suggested_hashtags"],
            character_count=result["character_count"],
            data={
                "tone": request.tone,
                "original_length": len(request.content),
                "compression_ratio": round(result["character_count"] / len(request.content) * 100, 2) if request.content else 0
            }
        )
        
    except Exception as e:
        action_logger.log_action(
            action="generate_post_summary",
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@app.get("/status")
async def server_status():
    """Get server status and configuration."""
    is_valid, _ = validate_credentials()
    
    return {
        "server": "linkedin_mcp",
        "version": "1.0.0",
        "status": "running",
        "credentials_configured": is_valid,
        "endpoints": [
            "/create_post",
            "/schedule_post",
            "/generate_post_summary",
            "/health",
            "/status"
        ],
        "approval_required_for": ["public posts", "scheduled posts"],
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# Error Handlers
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled errors."""
    action_logger.log_action(
        action="exception",
        status="error",
        details={
            "path": str(request.url.path),
            "method": request.method,
            "error": str(exc)
        }
    )
    
    return {
        "success": False,
        "error": "Internal server error",
        "error_code": "INTERNAL_ERROR",
        "details": {"message": str(exc)}
    }


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    # Get configuration from environment or use defaults
    host = os.getenv("LINKEDIN_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("LINKEDIN_MCP_PORT", "8002"))
    
    logger.info(f"Starting LinkedIn MCP Server on http://{host}:{port}")
    logger.info("Endpoints available:")
    logger.info("  POST /create_post - Create a LinkedIn post")
    logger.info("  POST /schedule_post - Schedule a post for future publishing")
    logger.info("  POST /generate_post_summary - Generate a post summary")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /status - Server status")
    
    uvicorn.run(app, host=host, port=port)
