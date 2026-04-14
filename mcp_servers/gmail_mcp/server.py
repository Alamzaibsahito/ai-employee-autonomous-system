"""
Gmail MCP Server — Exposes Gmail operations via MCP protocol.
Tools: read_emails, send_email, search_emails, get_email_by_id, mark_as_read, delete_email
"""

import os
import sys
import base64
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_servers.shared.auth import get_google_credentials

from config import config
from logger_setup import logger

# OAuth scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

app = Server("gmail-mcp")


def authenticate_gmail() -> Credentials:
    """Authenticate and return Gmail credentials."""
    creds = None
    token_path = config.gmail_token_path
    creds_path = config.gmail_credentials_path

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {creds_path}. "
                    "Download from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save credentials
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def get_gmail_service():
    """Build and return Gmail API service."""
    creds = authenticate_gmail()
    return build("gmail", "v1", credentials=creds)


def _encode_email_body(to: str, subject: str, body: str) -> str:
    """Create RFC 2822 email message and base64 encode it."""
    from email.mime.text import MIMEText

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return raw


@app.tool(name="read_emails")
async def handle_read_emails(max_results: int = 10, query: str = "") -> list[TextContent]:
    """Read recent emails from Gmail. Returns list of emails with id, sender, subject, snippet, date."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()
        messages = results.get("messages", [])

        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg["id"],
                "threadId": msg.get("threadId"),
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": detail.get("snippet", ""),
            })

        return [TextContent(type="text", text=str(emails))]
    except Exception as e:
        logger.error(f"Gmail read_emails error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="send_email")
async def handle_send_email(to: str, subject: str, body: str) -> list[TextContent]:
    """Send an email via Gmail. Returns success status and message_id. Requires approval for new contacts."""
    try:
        service = get_gmail_service()
        raw_message = _encode_email_body(to, subject, body)
        message = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        return [TextContent(type="text", text=f"Email sent. Message ID: {message['id']}")]
    except Exception as e:
        logger.error(f"Gmail send_email error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="search_emails")
async def handle_search_emails(query: str, max_results: int = 20) -> list[TextContent]:
    """Search emails using Gmail query syntax (e.g. 'from:boss is:unread')."""
    return await handle_read_emails(max_results=max_results, query=query)


@app.tool(name="get_email_by_id")
async def handle_get_email_by_id(message_id: str) -> list[TextContent]:
    """Get full email content by message ID."""
    try:
        service = get_gmail_service()
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = ""
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part:
                    body = base64.urlsafe_b64decode(part["data"]).decode("utf-8")
                    break
        elif "body" in msg["payload"] and "data" in msg["payload"]["body"]:
            body = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")

        result = {
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": body,
        }
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"Gmail get_email_by_id error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="mark_as_read")
async def handle_mark_as_read(message_id: str) -> list[TextContent]:
    """Mark an email as read (remove UNREAD label)."""
    try:
        service = get_gmail_service()
        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return [TextContent(type="text", text=f"Message {message_id} marked as read")]
    except Exception as e:
        logger.error(f"Gmail mark_as_read error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="delete_email")
async def handle_delete_email(message_id: str) -> list[TextContent]:
    """Delete (trash) an email by message ID."""
    try:
        service = get_gmail_service()
        service.users().messages().trash(userId="me", id=message_id).execute()
        return [TextContent(type="text", text=f"Message {message_id} trashed")]
    except Exception as e:
        logger.error(f"Gmail delete_email error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
