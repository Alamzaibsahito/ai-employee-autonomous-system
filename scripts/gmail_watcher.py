"""
Gmail Watcher — Monitors inbox for new/unread emails and creates tasks in vault Inbox.
Polls Gmail API at configurable intervals. Detects new emails by tracking seen message IDs.
"""

import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger
from mcp_servers.gmail_mcp.server import authenticate_gmail
from googleapiclient.discovery import build

# State file to track processed emails
STATE_FILE = FOLDERS["logs"] / "gmail_state.json"


def load_state() -> dict:
    """Load processed email IDs from state file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"processed_ids": [], "last_check": None}


def save_state(state: dict):
    """Save processed email IDs to state file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_important_email(headers: dict, snippet: str) -> bool:
    """Simple heuristic to determine if email needs action."""
    important_keywords = [
        "urgent", "action required", "approval", "deadline",
        "asap", "please review", "need your", "follow up",
    ]
    subject = headers.get("Subject", "").lower()
    sender = headers.get("From", "").lower()
    snippet_lower = snippet.lower()

    # Check for important keywords
    for kw in important_keywords:
        if kw in subject or kw in snippet_lower:
            return True

    # Check if from known important sender (customize as needed)
    important_domains = ["company.com", "client.com", "boss.com"]
    for domain in important_domains:
        if domain in sender:
            return True

    return False


def create_task_file(email_data: dict) -> str:
    """Create a task markdown file in the Inbox folder."""
    task_id = f"GMAIL_{email_data['id'][:8].upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task_file = FOLDERS["inbox"] / f"{task_id}.md"

    content = f"""---
task_id: {task_id}
source: gmail_watcher
created: {datetime.now(timezone.utc).isoformat()}
status: inbox
priority: {'high' if email_data.get('important') else 'normal'}
email_id: {email_data['id']}
from: {email_data['from']}
subject: {email_data['subject']}
---

# Task: {email_data['subject']}

**Source:** Gmail Watcher
**From:** {email_data['from']}
**Date:** {email_data['date']}
**Email ID:** {email_data['id']}

## Summary
{email_data['snippet']}

## Action Required
> [!TODO] Review email and determine required action

## Notes
- Auto-created by Gmail Watcher
- Priority: {'HIGH — contains important keywords' if email_data.get('important') else 'Normal'}
"""
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(content)

    return task_id


def check_gmail():
    """Poll Gmail for new emails and create tasks for important ones."""
    ensure_folders()
    state = load_state()
    logger.info("Gmail Watcher: Checking for new emails...")

    try:
        creds = authenticate_gmail()
        service = build("gmail", "v1", credentials=creds)

        # Get unread messages
        results = service.users().messages().list(
            userId="me", maxResults=25, q="is:unread"
        ).execute()
        messages = results.get("messages", [])

        new_tasks = 0
        for msg in messages:
            if msg["id"] in state["processed_ids"]:
                continue

            # Get message details
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            snippet = detail.get("snippet", "")

            important = is_important_email(headers, snippet)
            email_data = {
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": snippet,
                "important": important,
            }

            if important:
                task_id = create_task_file(email_data)
                audit_log(
                    action="gmail_new_email_task_created",
                    task_id=task_id,
                    details={"from": email_data["from"], "subject": email_data["subject"]},
                )
                logger.info(f"Gmail Watcher: Created task {task_id} for email from {email_data['from']}")
                new_tasks += 1

            state["processed_ids"].append(msg["id"])

        # Keep only last 500 IDs to prevent state file bloat
        state["processed_ids"] = state["processed_ids"][-500:]
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

        logger.info(f"Gmail Watcher: Check complete. {new_tasks} new task(s) created.")

    except Exception as e:
        logger.error(f"Gmail Watcher error: {e}")
        audit_log(action="gmail_watcher_error", level="ERROR", details={"error": str(e)})


def run_gmail_watcher(poll_interval: int = 60):
    """Run Gmail watcher in continuous polling loop."""
    logger.info(f"Gmail Watcher started — polling every {poll_interval}s")
    audit_log(action="gmail_watcher_started", details={"poll_interval": poll_interval})

    while True:
        try:
            check_gmail()
        except Exception as e:
            logger.error(f"Gmail Watcher loop error: {e}")
        time.sleep(poll_interval)


if __name__ == "__main__":
    run_gmail_watcher()
