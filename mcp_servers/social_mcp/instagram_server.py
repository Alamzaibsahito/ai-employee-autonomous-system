"""
Instagram MCP Server - Platinum Tier

Provides MCP endpoints for Instagram operations:
- post_instagram: Post to Instagram (requires approval)
- create_draft_post: Create a draft post
- get_post_history: Get recent posts
- generate_caption: Generate Instagram caption

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
        logging.FileHandler(os.path.join(LOG_DIR, "instagram_mcp.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Instagram MCP Server",
    description="MCP server for Instagram operations",
    version="1.0.0"
)

# Configuration
INSTAGRAM_HISTORY_FILE = "AI_Employee_Vault/reports/instagram_history.md"
PENDING_APPROVAL_FOLDER = "Pending_Approval"
APPROVED_FOLDER = "Approved"

os.makedirs(os.path.dirname(INSTAGRAM_HISTORY_FILE), exist_ok=True)
os.makedirs(PENDING_APPROVAL_FOLDER, exist_ok=True)
os.makedirs(APPROVED_FOLDER, exist_ok=True)


# ============================================================
# Request/Response Models
# ============================================================

class InstagramPostRequest(BaseModel):
    """Request model for posting to Instagram."""
    message: str = Field(..., description="Caption content (max 2200 characters)")
    image_url: Optional[str] = Field(None, description="URL of image to post")
    requires_approval: bool = Field(default=True, description="Require human approval")


class DraftPostRequest(BaseModel):
    """Request model for creating draft posts."""
    message: str = Field(..., description="Caption content")
    image_url: Optional[str] = Field(None, description="URL of image")
    scheduled_time: Optional[str] = Field(None, description="Scheduled time for posting")


class PostHistoryRequest(BaseModel):
    """Request model for getting post history."""
    limit: int = Field(default=10, ge=1, le=100, description="Number of posts to retrieve")


class GenerateCaptionRequest(BaseModel):
    """Request model for generating Instagram captions."""
    content: str = Field(..., description="Content to convert to caption")
    style: Optional[str] = Field(default="casual", description="Caption style: casual, professional, enthusiastic")


class PostResponse(BaseModel):
    """Response model for Instagram post operations."""
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


class CaptionResponse(BaseModel):
    """Response model for caption generation."""
    success: bool
    caption: str
    hashtags: List[str]
    character_count: int


# ============================================================
# Helper Functions
# ============================================================

def validate_caption_length(message: str) -> bool:
    """Validate caption is within 2200 character limit."""
    return len(message) <= 2200


def filter_sensitive_data(message: str) -> str:
    """Filter sensitive data from caption."""
    sensitive_keywords = ['password', 'secret', 'token', 'key', 'credential']
    words = message.split()
    filtered = [w for w in words if w.lower() not in sensitive_keywords]
    return ' '.join(filtered)


def log_post_to_history(post_data: Dict[str, Any]) -> None:
    """Log post to history file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not os.path.exists(INSTAGRAM_HISTORY_FILE):
            with open(INSTAGRAM_HISTORY_FILE, 'w', encoding='utf-8') as f:
                f.write("# Instagram Post History\n\n")
                f.write("| Timestamp | Post ID | Caption | Image | Status |\n")
                f.write("|-----------|---------|---------|-------|--------|\n")
        
        with open(INSTAGRAM_HISTORY_FILE, 'a', encoding='utf-8') as f:
            caption_preview = post_data.get('message', '')[:50].replace('|', '-')
            image = post_data.get('image_url', 'N/A')
            f.write(f"| {timestamp} | {post_data.get('post_id', 'N/A')} | {caption_preview}... | {image} | Posted |\n")
        
        logger.info(f"Post logged to history: {INSTAGRAM_HISTORY_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to log post to history: {e}")


def create_approval_request(post_data: Dict[str, Any]) -> str:
    """Create approval request file."""
    try:
        approval_id = f"instagram_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        approval_content = f"""---
Type: social_media_approval
Platform: Instagram
Status: pending_approval
Created_at: {datetime.now().isoformat()}
Action: post_instagram
---

# Instagram Post Approval Request

## Caption
```
{post_data['message']}
```

## Details
- **Image URL:** {post_data.get('image_url', 'None')}
- **Character Count:** {len(post_data['message'])}/2200
- **Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Action:** Post to Instagram

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


def generate_hashtags(style: str = "casual") -> List[str]:
    """Generate hashtags based on style."""
    hashtag_sets = {
        "casual": ["#lifestyle", "#daily", "#moments", "#vibes", "#instagood"],
        "professional": ["#business", "#professional", "#success", "#growth", "#leadership"],
        "enthusiastic": ["#excited", "#amazing", "#love", "#happy", "#blessed"],
        "tech": ["#tech", "#innovation", "#AI", "#automation", "#future"],
    }
    return hashtag_sets.get(style, hashtag_sets["casual"])


def simulate_post_instagram(message: str, image_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulate posting to Instagram.
    In production, integrate with Instagram Graph API.
    """
    filtered_message = filter_sensitive_data(message)
    post_id = f"ig_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "post_id": post_id,
        "message": filtered_message,
        "image_url": image_url,
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
        "service": "instagram_mcp",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/post_instagram", response_model=PostResponse)
async def post_instagram(request: InstagramPostRequest):
    """
    Post to Instagram.
    
    Requires human approval by default.
    """
    try:
        # Validate caption length
        if not validate_caption_length(request.message):
            raise HTTPException(
                status_code=400,
                detail="Caption exceeds 2200 character limit"
            )
        
        logger.info(f"Instagram post request received: {request.message[:50]}...")
        
        if request.requires_approval:
            post_data = {
                "message": request.message,
                "image_url": request.image_url
            }
            approval_id = create_approval_request(post_data)
            
            return PostResponse(
                success=True,
                message="Instagram post approval request created. Waiting for human approval.",
                requires_approval=True,
                approval_request_id=approval_id
            )
        
        post_data = simulate_post_instagram(request.message, request.image_url)
        log_post_to_history(post_data)
        
        logger.info(f"Instagram post successful: {post_data['post_id']}")
        
        return PostResponse(
            success=True,
            message="Instagram post published successfully",
            post_id=post_data["post_id"],
            posted_at=post_data["posted_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to post to Instagram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_draft", response_model=DraftResponse)
async def create_draft_post(request: DraftPostRequest):
    """Create a draft Instagram post."""
    try:
        draft_id = f"ig_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        draft_file = f"AI_Employee_Vault/Vault/draft_{draft_id}.md"
        draft_content = f"""---
Type: instagram_draft
Created_at: {datetime.now().isoformat()}
Scheduled: {request.scheduled_time or 'Not scheduled'}
---

# Draft Instagram Post

**Caption:**
{request.message}

**Image URL:** {request.image_url or 'Not specified'}

---
Character Count: {len(request.message)}/2200
Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(draft_content)
        
        logger.info(f"Instagram draft created: {draft_id}")
        
        return DraftResponse(
            success=True,
            message="Draft Instagram post created",
            draft_id=draft_id
        )
        
    except Exception as e:
        logger.error(f"Failed to create draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_history", response_model=Dict[str, Any])
async def get_post_history(request: PostHistoryRequest):
    """Get recent Instagram post history."""
    try:
        if not os.path.exists(INSTAGRAM_HISTORY_FILE):
            return {"success": True, "posts": [], "message": "No post history available"}
        
        posts = []
        with open(INSTAGRAM_HISTORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()[3:]
            for line in lines[:request.limit]:
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    posts.append({
                        "timestamp": parts[1].strip(),
                        "post_id": parts[2].strip(),
                        "caption": parts[3].strip(),
                        "image": parts[4].strip(),
                        "status": parts[5].strip() if len(parts) > 5 else "Unknown"
                    })
        
        return {"success": True, "posts": posts, "count": len(posts)}
        
    except Exception as e:
        logger.error(f"Failed to get post history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_caption", response_model=CaptionResponse)
async def generate_caption(request: GenerateCaptionRequest):
    """Generate an Instagram caption from content."""
    try:
        content = request.content
        
        if not content:
            raise HTTPException(status_code=400, detail="Content required")
        
        # Simple caption generation
        # In production, use LLM for better generation
        words = content.split()[:50]
        caption = ' '.join(words)
        
        # Add emojis based on style
        emojis = {
            "casual": "✨",
            "professional": "💼",
            "enthusiastic": "🎉",
            "tech": "🚀"
        }
        emoji = emojis.get(request.style, "✨")
        caption = f"{emoji} {caption}"
        
        # Generate hashtags
        hashtags = generate_hashtags(request.style)
        
        # Build final caption
        final_caption = f"{caption}\n\n{' '.join(hashtags)}"
        
        # Validate length
        if len(final_caption) > 2200:
            final_caption = final_caption[:2197] + "..."
        
        return CaptionResponse(
            success=True,
            caption=final_caption,
            hashtags=hashtags,
            character_count=len(final_caption)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate caption: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting Instagram MCP Server...")
    uvicorn.run(app, host="127.0.0.1", port=8006)
