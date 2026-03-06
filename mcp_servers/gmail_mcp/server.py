"""
Gmail MCP Server

Provides Model Context Protocol (MCP) endpoints for Gmail operations:
- send_email: Send an email
- draft_email: Create a draft email
- read_recent_emails: Read recent emails from inbox

All actions are logged and require proper authentication.
Sensitive actions (sending emails) require human approval flag.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.auth import (
    get_credential_manager,
    create_action_logger,
    CredentialManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Gmail MCP Server",
    description="MCP server for Gmail operations",
    version="1.0.0"
)

# Initialize components
credential_manager = get_credential_manager()
action_logger = create_action_logger("gmail")


# ============================================================
# Request/Response Models
# ============================================================

class EmailRequest(BaseModel):
    """Request model for sending/drafting emails."""
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body content")
    cc: Optional[str] = Field(None, description="CC recipients (comma-separated)")
    bcc: Optional[str] = Field(None, description="BCC recipients (comma-separated)")
    requires_approval: bool = Field(
        default=True,
        description="Whether this email requires human approval before sending"
    )


class DraftRequest(BaseModel):
    """Request model for creating drafts."""
    to: Optional[str] = Field(None, description="Recipient email address")
    subject: Optional[str] = Field(None, description="Email subject")
    body: Optional[str] = Field(None, description="Email body content")
    labels: Optional[List[str]] = Field(None, description="Labels to apply to draft")


class ReadEmailsRequest(BaseModel):
    """Request model for reading recent emails."""
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of emails to retrieve")
    query: Optional[str] = Field(None, description="Gmail search query")
    include_body: bool = Field(default=True, description="Whether to include email body")


class EmailResponse(BaseModel):
    """Response model for email operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    approval_request_id: Optional[str] = None


class DraftResponse(BaseModel):
    """Response model for draft operations."""
    success: bool
    message: str
    draft_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ReadEmailsResponse(BaseModel):
    """Response model for reading emails."""
    success: bool
    message: str
    emails: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


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
    """Validate Gmail credentials are configured."""
    is_valid, message = credential_manager.validate_gmail_credentials()
    return is_valid, message


def simulate_gmail_send(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate sending an email via Gmail API.
    
    In production, this would integrate with the actual Gmail API.
    For now, it simulates the operation for testing purposes.
    """
    # Simulate API call
    message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    
    return {
        "id": message_id,
        "to": email_data.get("to"),
        "subject": email_data.get("subject"),
        "status": "sent",
        "timestamp": datetime.now().isoformat(),
        "thread_id": f"thread_{os.urandom(4).hex()}"
    }


def simulate_gmail_draft(draft_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate creating a draft via Gmail API.
    
    In production, this would integrate with the actual Gmail API.
    """
    draft_id = f"draft_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    
    return {
        "id": draft_id,
        "message": {
            "to": draft_data.get("to"),
            "subject": draft_data.get("subject"),
            "body": draft_data.get("body"),
            "labels": draft_data.get("labels", ["DRAFT"])
        },
        "timestamp": datetime.now().isoformat()
    }


def simulate_gmail_read(max_results: int, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Simulate reading emails from Gmail.
    
    In production, this would integrate with the actual Gmail API.
    """
    # Return simulated emails for testing
    emails = []
    for i in range(min(max_results, 5)):  # Return up to 5 sample emails
        emails.append({
            "id": f"email_{i}_{os.urandom(4).hex()}",
            "from": f"sender{i}@example.com",
            "subject": f"Sample Email {i + 1}",
            "snippet": f"This is a sample email snippet for email {i + 1}...",
            "date": datetime.now().isoformat(),
            "labels": ["INBOX", "UNREAD"] if i % 2 == 0 else ["INBOX"],
            "body": f"Full email body content for email {i + 1}" if max_results > 0 else None
        })
    
    return emails


def create_approval_request(action: str, email_data: Dict[str, Any]) -> str:
    """
    Create an approval request for sensitive actions.
    
    Returns the approval request ID.
    """
    approval_id = f"approval_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
    
    # In production, this would create a file in Pending_Approval/ folder
    # For now, we just log the request
    action_logger.log_action(
        action="create_approval_request",
        status="pending",
        details={
            "approval_id": approval_id,
            "action": action,
            "email_data": {
                "to": email_data.get("to"),
                "subject": email_data.get("subject")
            }
        }
    )
    
    return approval_id


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server": "gmail_mcp",
        "timestamp": datetime.now().isoformat(),
        "credentials_configured": credential_manager.gmail_client_id is not None
    }


@app.post("/send_email", response_model=EmailResponse)
async def send_email(request: EmailRequest, x_approval_status: Optional[str] = Header(None)):
    """
    Send an email via Gmail.
    
    This is a sensitive action that requires human approval.
    The x_approval_status header should contain 'approved' if approval was obtained.
    
    Args:
        request: Email request with to, subject, body, etc.
        x_approval_status: Approval status header (optional)
    
    Returns:
        EmailResponse with success status and message ID
    """
    action_logger.log_request(
        endpoint="/send_email",
        method="POST",
        payload={"to": request.to, "subject": request.subject, "requires_approval": request.requires_approval}
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="send_email",
            status="error",
            details={"error": error_msg, "to": request.to}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    # Check if approval is required
    if request.requires_approval:
        if x_approval_status != "approved":
            # Create approval request
            approval_id = create_approval_request("send_email", request.dict())
            
            action_logger.log_action(
                action="send_email",
                status="pending_approval",
                details={"to": request.to, "subject": request.subject, "approval_id": approval_id}
            )
            
            return EmailResponse(
                success=False,
                message="Email requires human approval before sending",
                requires_approval=True,
                approval_request_id=approval_id
            )
    
    # Send the email
    try:
        email_data = {
            "to": request.to,
            "subject": request.subject,
            "body": request.body,
            "cc": request.cc,
            "bcc": request.bcc
        }
        
        result = simulate_gmail_send(email_data)
        
        action_logger.log_action(
            action="send_email",
            status="success",
            details={"to": request.to, "subject": request.subject, "message_id": result["id"]}
        )
        
        action_logger.log_response(
            endpoint="/send_email",
            status_code=200,
            response={"success": True, "message_id": result["id"]}
        )
        
        return EmailResponse(
            success=True,
            message="Email sent successfully",
            data=result
        )
        
    except Exception as e:
        action_logger.log_action(
            action="send_email",
            status="error",
            details={"to": request.to, "error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/draft_email", response_model=DraftResponse)
async def draft_email(request: DraftRequest):
    """
    Create a draft email in Gmail.
    
    Args:
        request: Draft request with optional to, subject, body, labels
    
    Returns:
        DraftResponse with draft ID
    """
    action_logger.log_request(
        endpoint="/draft_email",
        method="POST",
        payload=request.dict()
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="draft_email",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        draft_data = {
            "to": request.to,
            "subject": request.subject,
            "body": request.body,
            "labels": request.labels
        }
        
        result = simulate_gmail_draft(draft_data)
        
        action_logger.log_action(
            action="draft_email",
            status="success",
            details={"draft_id": result["id"], "subject": request.subject}
        )
        
        action_logger.log_response(
            endpoint="/draft_email",
            status_code=200,
            response={"success": True, "draft_id": result["id"]}
        )
        
        return DraftResponse(
            success=True,
            message="Draft created successfully",
            draft_id=result["id"],
            data=result
        )
        
    except Exception as e:
        action_logger.log_action(
            action="draft_email",
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create draft: {str(e)}")


@app.post("/read_recent_emails", response_model=ReadEmailsResponse)
async def read_recent_emails(request: ReadEmailsRequest):
    """
    Read recent emails from Gmail inbox.
    
    Args:
        request: Read request with max_results, query, include_body
    
    Returns:
        ReadEmailsResponse with list of emails
    """
    action_logger.log_request(
        endpoint="/read_recent_emails",
        method="POST",
        payload={"max_results": request.max_results, "query": request.query}
    )
    
    # Validate credentials
    is_valid, error_msg = validate_credentials()
    if not is_valid:
        action_logger.log_action(
            action="read_recent_emails",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        emails = simulate_gmail_read(
            max_results=request.max_results,
            query=request.query
        )
        
        # Filter out body if not requested
        if not request.include_body:
            for email in emails:
                email.pop("body", None)
        
        action_logger.log_action(
            action="read_recent_emails",
            status="success",
            details={"count": len(emails), "query": request.query}
        )
        
        action_logger.log_response(
            endpoint="/read_recent_emails",
            status_code=200,
            response={"success": True, "count": len(emails)}
        )
        
        return ReadEmailsResponse(
            success=True,
            message=f"Retrieved {len(emails)} emails",
            emails=emails,
            count=len(emails)
        )
        
    except Exception as e:
        action_logger.log_action(
            action="read_recent_emails",
            status="error",
            details={"error": str(e)}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to read emails: {str(e)}")


@app.get("/status")
async def server_status():
    """Get server status and configuration."""
    is_valid, _ = validate_credentials()
    
    return {
        "server": "gmail_mcp",
        "version": "1.0.0",
        "status": "running",
        "credentials_configured": is_valid,
        "endpoints": [
            "/send_email",
            "/draft_email",
            "/read_recent_emails",
            "/health",
            "/status"
        ],
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
    host = os.getenv("GMAIL_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("GMAIL_MCP_PORT", "8001"))
    
    logger.info(f"Starting Gmail MCP Server on http://{host}:{port}")
    logger.info("Endpoints available:")
    logger.info("  POST /send_email - Send an email")
    logger.info("  POST /draft_email - Create a draft email")
    logger.info("  POST /read_recent_emails - Read recent emails")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /status - Server status")
    
    uvicorn.run(app, host=host, port=port)
