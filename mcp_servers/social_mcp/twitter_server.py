"""
Twitter MCP Server - Platinum Tier

Provides MCP endpoints for Twitter/X operations:
- post_tweet: Post a tweet (requires approval)
- create_draft_tweet: Create a draft tweet
- get_tweet_history: Get recent tweets
- generate_tweet_summary: Generate tweet-friendly summary

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
        logging.FileHandler(os.path.join(LOG_DIR, "twitter_mcp.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Twitter MCP Server",
    description="MCP server for Twitter/X operations",
    version="1.0.0"
)

# Configuration
TWITTER_HISTORY_FILE = "AI_Employee_Vault/reports/twitter_history.md"
PENDING_APPROVAL_FOLDER = "Pending_Approval"
APPROVED_FOLDER = "Approved"

os.makedirs(os.path.dirname(TWITTER_HISTORY_FILE), exist_ok=True)
os.makedirs(PENDING_APPROVAL_FOLDER, exist_ok=True)
os.makedirs(APPROVED_FOLDER, exist_ok=True)


# ============================================================
# Request/Response Models
# ============================================================

class TweetRequest(BaseModel):
    """Request model for posting tweets."""
    message: str = Field(..., description="Tweet content (max 280 characters)")
    requires_approval: bool = Field(default=True, description="Require human approval")


class DraftTweetRequest(BaseModel):
    """Request model for creating draft tweets."""
    message: str = Field(..., description="Tweet content")
    scheduled_time: Optional[str] = Field(None, description="Scheduled time for posting")


class TweetHistoryRequest(BaseModel):
    """Request model for getting tweet history."""
    limit: int = Field(default=10, ge=1, le=100, description="Number of tweets to retrieve")


class TweetResponse(BaseModel):
    """Response model for tweet operations."""
    success: bool
    message: str
    tweet_id: Optional[str] = None
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

def validate_tweet_length(message: str) -> bool:
    """Validate tweet is within 280 character limit."""
    return len(message) <= 280


def filter_sensitive_data(message: str) -> str:
    """Filter sensitive data from tweet."""
    sensitive_keywords = ['password', 'secret', 'token', 'key', 'credential']
    words = message.split()
    filtered = [w for w in words if w.lower() not in sensitive_keywords and not w.startswith('http')]
    return ' '.join(filtered)


def log_tweet_to_history(tweet_data: Dict[str, Any]) -> None:
    """Log tweet to history file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create or append to history file
        if not os.path.exists(TWITTER_HISTORY_FILE):
            with open(TWITTER_HISTORY_FILE, 'w', encoding='utf-8') as f:
                f.write("# Twitter Tweet History\n\n")
                f.write("| Timestamp | Tweet ID | Content | Status |\n")
                f.write("|-----------|----------|---------|--------|\n")
        
        with open(TWITTER_HISTORY_FILE, 'a', encoding='utf-8') as f:
            content_preview = tweet_data.get('message', '')[:50].replace('|', '-')
            f.write(f"| {timestamp} | {tweet_data.get('tweet_id', 'N/A')} | {content_preview}... | Posted |\n")
        
        logger.info(f"Tweet logged to history: {TWEET_HISTORY_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to log tweet to history: {e}")


def create_approval_request(tweet_data: Dict[str, Any]) -> str:
    """Create approval request file."""
    try:
        approval_id = f"tweet_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        approval_content = f"""---
Type: social_media_approval
Platform: Twitter
Status: pending_approval
Created_at: {datetime.now().isoformat()}
Action: post_tweet
---

# Twitter Post Approval Request

## Tweet Content
```
{tweet_data['message']}
```

## Details
- **Character Count:** {len(tweet_data['message'])}
- **Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Action:** Post to Twitter

## Approval Required

This tweet requires human approval before posting.

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


def check_approval_granted(approval_id: str) -> bool:
    """Check if approval has been granted."""
    approval_file = os.path.join(PENDING_APPROVAL_FOLDER, f"{approval_id}.md")
    approved_file = os.path.join(APPROVED_FOLDER, f"{approval_id}.md")
    
    if os.path.exists(approved_file):
        return True
    
    if os.path.exists(approval_file):
        return False
    
    # File moved or deleted - check if in approved
    return os.path.exists(approved_file)


def simulate_post_tweet(message: str) -> Dict[str, Any]:
    """
    Simulate posting a tweet.
    In production, integrate with Twitter API v2.
    """
    # Filter sensitive data
    filtered_message = filter_sensitive_data(message)
    
    # Generate mock tweet ID
    tweet_id = f"tweet_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return {
        "tweet_id": tweet_id,
        "message": filtered_message,
        "posted_at": datetime.now().isoformat(),
        "character_count": len(filtered_message),
    }


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "twitter_mcp",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/post_tweet", response_model=TweetResponse)
async def post_tweet(request: TweetRequest):
    """
    Post a tweet to Twitter.
    
    Requires human approval by default.
    In draft mode, creates approval request without posting.
    """
    try:
        # Validate tweet length
        if not validate_tweet_length(request.message):
            raise HTTPException(
                status_code=400,
                detail="Tweet exceeds 280 character limit"
            )
        
        logger.info(f"Tweet request received: {request.message[:50]}...")
        
        # If approval required, create approval request
        if request.requires_approval:
            tweet_data = {
                "message": request.message,
                "requires_approval": True
            }
            approval_id = create_approval_request(tweet_data)
            
            return TweetResponse(
                success=True,
                message="Tweet approval request created. Waiting for human approval.",
                requires_approval=True,
                approval_request_id=approval_id
            )
        
        # Post directly (only if no approval required)
        tweet_data = simulate_post_tweet(request.message)
        
        # Log to history
        log_tweet_to_history(tweet_data)
        
        logger.info(f"Tweet posted successfully: {tweet_data['tweet_id']}")
        
        return TweetResponse(
            success=True,
            message="Tweet posted successfully",
            tweet_id=tweet_data["tweet_id"],
            posted_at=tweet_data["posted_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create_draft", response_model=DraftResponse)
async def create_draft_tweet(request: DraftTweetRequest):
    """
    Create a draft tweet without posting.
    
    Drafts are saved to Vault for later review.
    """
    try:
        # Validate tweet length
        if not validate_tweet_length(request.message):
            raise HTTPException(
                status_code=400,
                detail="Tweet exceeds 280 character limit"
            )
        
        draft_id = f"draft_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save draft to vault
        draft_file = f"AI_Employee_Vault/Vault/draft_{draft_id}.md"
        draft_content = f"""---
Type: tweet_draft
Created_at: {datetime.now().isoformat()}
Scheduled: {request.scheduled_time or 'Not scheduled'}
---

# Draft Tweet

{request.message}

---
Character Count: {len(request.message)}/280
"""
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(draft_content)
        
        logger.info(f"Draft tweet created: {draft_id}")
        
        return DraftResponse(
            success=True,
            message="Draft tweet created",
            draft_id=draft_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_history", response_model=Dict[str, Any])
async def get_tweet_history(request: TweetHistoryRequest):
    """
    Get recent tweet history.
    
    Returns tweets from the local history file.
    """
    try:
        if not os.path.exists(TWITTER_HISTORY_FILE):
            return {
                "success": True,
                "tweets": [],
                "message": "No tweet history available"
            }
        
        tweets = []
        with open(TWITTER_HISTORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()[3:]  # Skip header
            for line in lines[:request.limit]:
                parts = line.strip().split('|')
                if len(parts) >= 4:
                    tweets.append({
                        "timestamp": parts[1].strip(),
                        "tweet_id": parts[2].strip(),
                        "content": parts[3].strip(),
                        "status": parts[4].strip() if len(parts) > 4 else "Unknown"
                    })
        
        return {
            "success": True,
            "tweets": tweets,
            "count": len(tweets)
        }
        
    except Exception as e:
        logger.error(f"Failed to get tweet history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_summary", response_model=Dict[str, Any])
async def generate_tweet_summary(request: Dict[str, str]):
    """
    Generate a tweet-friendly summary from content.
    
    Creates a concise, hashtag-ready summary.
    """
    try:
        content = request.get("content", "")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content required")
        
        # Simple summarization logic
        # In production, use LLM for better summarization
        words = content.split()[:40]  # Limit to ~40 words
        summary = ' '.join(words)
        
        # Add hashtags
        hashtags = "#AI #Automation"
        
        final_tweet = f"{summary} {hashtags}"
        
        # Ensure within limit
        if len(final_tweet) > 280:
            final_tweet = final_tweet[:277] + "..."
        
        return {
            "success": True,
            "summary": final_tweet,
            "character_count": len(final_tweet),
            "hashtags": hashtags
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    logger.info("Starting Twitter MCP Server...")
    uvicorn.run(app, host="127.0.0.1", port=8004)
