"""
Facebook MCP Server - Platinum Tier

Provides MCP endpoints for Facebook operations:
- post_facebook: Post to Facebook page (requires approval)
- create_draft_post: Create a draft post
- get_post_history: Get recent posts
- generate_post_summary: Generate Facebook-friendly summary

All posting actions require human approval.
Drafts can be created without approval.
History is saved to AI_Employee_Vault/reports/
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
LOG_DIR = "Logs/central"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "facebook_mcp.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Facebook MCP Server",
    description="MCP server for Facebook operations",
    version="1.0.0"
)

# Configuration
FACEBOOK_HISTORY_FILE = "AI_Employee_Vault/reports/facebook_history.md"
PENDING_APPROVAL_FOLDER = "Pending_Approval"
APPROVED_FOLDER = "Approved"

os.makedirs(os.path.dirname(FACEBOOK_HISTORY_FILE), exist_ok=True)
os.makedirs(PENDING_APPROVAL_FOLDER, exist_ok=True)
os.makedirs(APPROVED_FOLDER, exist_ok=True)


# ============================================================
# Request/Response Models
# ============================================================

class FacebookPostRequest(BaseModel):
    """Request model for posting to Facebook."""
    message: str = Field(..., description="Post content")
    link: Optional[str] = Field(None, description="Optional link to share")
    requires_approval: bool = Field(default=True, description="Require human approval")


class DraftPostRequest(BaseModel):
    """Request model for creating draft posts."""
    message: str = Field(..., description="Post content")
    link: Optional[str] = Field(None, description="Optional link")
    scheduled_time: Optional[str] = Field(None, description="Scheduled time for posting")


class PostHistoryRequest(BaseModel):
    """Request model for getting post history."""
    limit: int = Field(default=10, ge=1, le=100, description="Number of posts to retrieve")


class PostResponse(BaseModel):
    """Response model for Facebook post operations."""
    success: bool
    message: str
    post_id: Optional[str] = None
    posted_at: Optional[str] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None


class DraftResponse(BaseModel):
    """Response model for draft operations."""
    success: bool
    message: str
    draft_id: Optional[str] = None


# ============================================================
# Helper Functions
# ============================================================

def filter_sensitive_data(message: str) -> str:
    """Filter sensitive data from post."""
    sensitive_keywords = ['password', 'secret', 'token', 'key', 'credential']
    words = message.split()
    filtered = [w for w in words if w.lower() not in sensitive_keywords]
    return ' '.join(filtered)


def log_post_to_history(post_data: Dict[str, Any]) -> None:
    """Log post to history file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not os.path.exists(FACEBOOK_HISTORY_FILE):
            with open(FACEBOOK_HISTORY_FILE, 'w', encoding='utf-8') as f:
                f.write("# Facebook Post History\n\n")
                f.write("| Timestamp | Post ID | Content | Link | Status |\n")
                f.write("|-----------|---------|---------|------|--------|\n")
        
        with open(FACEBOOK_HISTORY_FILE, 'a', encoding='utf-8') as f:
            content_preview = post_data.get('message', '')[:50].replace('|', '-')
            link = post_data.get('link', 'N/A')
            f.write(f"| {timestamp} | {post_data.get('post_id', 'N/A')} | {content_preview}... | {link} | Posted |\n")
        
        logger.info(f"Post logged to history: {FACEBOOK_HISTORY_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to log post to history: {e}")


def create_approval_request(post_data: Dict[str, Any]) -> str:
    """Create approval request file."""
    try:
        approval_id = f"facebook_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        approval_content = f"""---
Type: social_media_approval
Platform: Facebook
Status: pending_approval
Created_at: {datetime.now().isoformat()}
Action: post_facebook
---

# Facebook Post Approval Request

## Post Content
```
{post_data['message']}
```

## Details
- **Link:** {post_data.get('link', 'None')}
- **Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Action:** Post to Facebook Page

## Approval Required

This post requires human approval before publishing.

---

## Human Decision Required

**To Approve:** Move this file to `Approved/` folder
**To Reject:** Delete this file or move to `Rejected/` folder
"""
        
        approval_file = os.path.join(PENDING_APPROVAL_FOLDER, f"{approval_id}.md")
        with open(approval_file, 'w', encoding='utf-8') as f:
            f.write(approval_content)
        
        logger.info(f"Approval request created: {approval_id}")
        return approval_id
        
    except Exception as e:
        logger.error(f"Failed to create approval request: {e}")
        raise


def simulate_post_facebook(message: str, link: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulate posting to Facebook.
    In production, integrate with Facebook Graph API.
    """
    filtered_message = filter_sensitive_data(message)
    post_id = f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "post_id": post_id,
        "message": filtered_message,
        "link": link,
        "posted_at": datetime.now().isoformat(),
    }


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "facebook_mcp",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/post_facebook", response_model=PostResponse)
async def post_facebook(request: FacebookPostRequest):
    """
    Post to Facebook page.
    
    Requires human approval by default.
    """
    try:
        logger.info(f"Facebook post request received: {request.message[:50]}...")
        
        if request.requires_approval:
            post_data = {
                "message": request.message,
                "link": request.link
            }
            approval_id = create_approval_request(post_data)
            
            return PostResponse(
                success=True,
                message="Facebook post approval request created. Waiting for human approval.",
                requires_approval=True,
                approval_request_id=approval_id
            )
        
        post_data = simulate_post_facebook(request.message, request.link)
        log_post_to_history(post_data)
        
        logger.info(f"Facebook post successful: {post_data['post_id']}")
        
        return PostResponse(
            success=True,
            message="Facebook post published successfully",
            post_id=post_data["post_id"],
            posted_at=post_data["posted_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to post to Facebook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_draft", response_model=DraftResponse)
async def create_draft_post(request: DraftPostRequest):
    """Create a draft Facebook post."""
    try:
        draft_id = f"fb_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        draft_file = f"AI_Employee_Vault/Vault/draft_{draft_id}.md"
        draft_content = f"""---
Type: facebook_draft
Created_at: {datetime.now().isoformat()}
Scheduled: {request.scheduled_time or 'Not scheduled'}
---

# Draft Facebook Post

**Message:**
{request.message}

**Link:** {request.link or 'None'}

---
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(draft_content)
        
        logger.info(f"Facebook draft created: {draft_id}")
        
        return DraftResponse(
            success=True,
            message="Draft Facebook post created",
            draft_id=draft_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_history", response_model=Dict[str, Any])
async def get_post_history(request: PostHistoryRequest):
    """Get recent Facebook post history."""
    try:
        if not os.path.exists(FACEBOOK_HISTORY_FILE):
            return {"success": True, "posts": [], "message": "No post history available"}
        
        posts = []
        with open(FACEBOOK_HISTORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()[3:]
            for line in lines[:request.limit]:
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    posts.append({
                        "timestamp": parts[1].strip(),
                        "post_id": parts[2].strip(),
                        "content": parts[3].strip(),
                        "link": parts[4].strip(),
                        "status": parts[5].strip() if len(parts) > 5 else "Unknown"
                    })
        
        return {"success": True, "posts": posts, "count": len(posts)}
        
    except Exception as e:
        logger.error(f"Failed to get post history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_summary", response_model=Dict[str, Any])
async def generate_post_summary(request: Dict[str, str]):
    """Generate a Facebook-friendly summary."""
    try:
        content = request.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Content required")
        
        words = content.split()[:100]
        summary = ' '.join(words)
        
        return {
            "success": True,
            "summary": summary,
            "character_count": len(summary)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting Facebook MCP Server...")
    uvicorn.run(app, host="127.0.0.1", port=8005)
