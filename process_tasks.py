import os
import datetime
import re
import time
import shutil
import requests
import yaml
import asyncio
import sys
from pathlib import Path

# --- Configuration ---
NEEDS_ACTION_FOLDER = "Needs_Action"
DONE_FOLDER = "Done"
APPROVED_FOLDER = "Approved"
COMPLETED_FOLDER = "Completed"
LOGS_FOLDER = "Logs"
SYSTEM_LOG_FILE = os.path.join(LOGS_FOLDER, "System_Log.md")

# LinkedIn MCP Server Configuration (fallback)
LINKEDIN_MCP_HOST = os.environ.get("LINKEDIN_MCP_HOST", "127.0.0.1")
LINKEDIN_MCP_PORT = int(os.environ.get("LINKEDIN_MCP_PORT", "8002"))
LINKEDIN_MCP_URL = f"http://{LINKEDIN_MCP_HOST}:{LINKEDIN_MCP_PORT}"

# LinkedIn Session Folder
LINKEDIN_SESSION_FOLDER = os.environ.get(
    "LINKEDIN_SESSION_FOLDER",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "linkedin_session")
)


def ensure_directories_exist():
    """
    Creates the necessary folders for the script to run if they don't already exist.
    This prevents errors when trying to read from or write to these directories.
    """
    os.makedirs(NEEDS_ACTION_FOLDER, exist_ok=True)
    os.makedirs(DONE_FOLDER, exist_ok=True)
    os.makedirs(APPROVED_FOLDER, exist_ok=True)
    os.makedirs(COMPLETED_FOLDER, exist_ok=True)
    os.makedirs(LOGS_FOLDER, exist_ok=True)


def log_task_processing(filename, status):
    """
    Appends a log entry to the system log file.

    Args:
        filename (str): The name of the task file being processed.
        status (str): The resulting status of the task ('done' or 'pending').
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] PROCESS_TASK – {filename} – {status}\n"

    try:
        with open(SYSTEM_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except IOError as e:
        print(f"Error: Could not write to log file {SYSTEM_LOG_FILE}. Reason: {e}")


def log_approval_execution(filename, status, message=""):
    """
    Appends a log entry for approval execution to the system log file.

    Args:
        filename (str): The name of the approval file being processed.
        status (str): The execution status ('executing', 'completed', 'failed').
        message (str): Additional message about the execution.
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] APPROVAL_EXECUTION – {filename} – {status}"
    if message:
        log_message += f" – {message}"
    log_message += "\n"

    try:
        with open(SYSTEM_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except IOError as e:
        print(f"Error: Could not write to log file {SYSTEM_LOG_FILE}. Reason: {e}")


def parse_yaml_frontmatter(content):
    """
    Parse YAML frontmatter from markdown content.

    Args:
        content (str): The markdown content with YAML frontmatter.

    Returns:
        dict: Parsed YAML metadata, or empty dict if no frontmatter found.
    """
    frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if frontmatter_match:
        try:
            yaml_content = frontmatter_match.group(1)
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            return {}
    return {}


def extract_post_content(approval_content):
    """
    Extract post content from approval file.

    Args:
        approval_content (str): The full content of the approval file.

    Returns:
        dict: Dictionary with post text, title, hashtags, and visibility.
    """
    post_data = {
        "text": "",
        "title": None,
        "hashtags": [],
        "visibility": "public"
    }

    # Extract content from "## Proposed Content" section
    proposed_match = re.search(
        r'## Proposed Content\s*\n(.*?)(?=##|\Z)',
        approval_content,
        re.DOTALL | re.IGNORECASE
    )
    if proposed_match:
        post_data["text"] = proposed_match.group(1).strip()

    # Extract hashtags
    hashtags_match = re.search(
        r'## Hashtags\s*\n(.*?)(?=##|\Z)',
        approval_content,
        re.DOTALL | re.IGNORECASE
    )
    if hashtags_match:
        hashtags_text = hashtags_match.group(1).strip()
        if hashtags_text.lower() != "none":
            post_data["hashtags"] = [
                tag.strip().lstrip('#')
                for tag in hashtags_text.split(',')
                if tag.strip()
            ]

    return post_data


def execute_linkedin_post(post_data):
    """
    Execute LinkedIn post via MCP server.

    Args:
        post_data (dict): Dictionary with post content.

    Returns:
        tuple: (success: bool, message: str, post_id: str or None)
    """
    try:
        payload = {
            "content": {
                "text": post_data.get("text", ""),
                "title": post_data.get("title"),
                "hashtags": post_data.get("hashtags", [])
            },
            "visibility": post_data.get("visibility", "public"),
            "requires_approval": False  # Already approved
        }

        response = requests.post(
            f"{LINKEDIN_MCP_URL}/create_post",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Approval-Status": "approved"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, "LinkedIn post successful", result.get("post_id")
            else:
                return False, f"LinkedIn post failed: {result.get('message', 'Unknown error')}", None
        else:
            return False, f"LinkedIn MCP server error: {response.status_code}", None

    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to LinkedIn MCP server at {LINKEDIN_MCP_URL}", None
    except requests.exceptions.Timeout:
        return False, "LinkedIn MCP server request timed out", None
    except Exception as e:
        return False, f"LinkedIn post error: {str(e)}", None


def process_approved_task(approval_filename):
    """
    Process an approved task file.
    Detects action_type and executes the appropriate action.

    Args:
        approval_filename (str): The filename of the approval in the Approved folder.
    """
    approval_filepath = os.path.join(APPROVED_FOLDER, approval_filename)

    try:
        with open(approval_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except IOError as e:
        print(f"Error: Could not read approval file {approval_filepath}. Reason: {e}")
        return False

    # Parse YAML frontmatter
    metadata = parse_yaml_frontmatter(content)

    # Get action type (case-insensitive lookup)
    action_type = ""
    for key in metadata:
        if key.lower() == "action_type":
            action_type = metadata[key]
            break
    action_type = (action_type or "").lower()

    if action_type != "linkedin_post":
        print(f"Approval '{approval_filename}' has unsupported action_type: {action_type}")
        log_approval_execution(approval_filename, "skipped", f"Unsupported action_type: {action_type}")
        return False

    print("Approved task detected")
    print("Executing LinkedIn approval task")
    log_approval_execution(approval_filename, "executing", "linkedin_post")

    # Extract post content
    post_data = extract_post_content(content)

    if not post_data.get("text"):
        print("Error: No post content found in approval file")
        log_approval_execution(approval_filename, "failed", "No post content")
        return False

    # Execute LinkedIn post
    success, message, post_id = execute_linkedin_post(post_data)

    if success:
        print(message)
        log_approval_execution(approval_filename, "completed", f"post_id: {post_id}")

        # Move to Completed folder
        completed_filepath = os.path.join(COMPLETED_FOLDER, approval_filename)
        try:
            # Add execution result to the file
            execution_result = f"\n\n---\n## Execution Result\nStatus: completed\nPost ID: {post_id}\nExecuted at: {datetime.datetime.now().isoformat()}\n"
            with open(approval_filepath, 'a', encoding='utf-8') as f:
                f.write(execution_result)

            # Move to Completed
            shutil.move(approval_filepath, completed_filepath)
            print(f"Approval '{approval_filename}' moved to '{COMPLETED_FOLDER}'")
        except (IOError, OSError) as e:
            print(f"Error: Could not move file to {COMPLETED_FOLDER}. Reason: {e}")

        return True
    else:
        print(message)
        log_approval_execution(approval_filename, "failed", message)
        return False


def process_single_task(task_filename):
    """
    Processes an individual task file. It checks for completion, updates status,
    and moves the file or adds next actions as needed.

    Args:
        task_filename (str): The filename of the task in the Needs_Action folder.
    """
    task_filepath = os.path.join(NEEDS_ACTION_FOLDER, task_filename)

    try:
        with open(task_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except IOError as e:
        print(f"Error: Could not read task file {task_filepath}. Reason: {e}")
        return

    # --- Parse Metadata and Checklist ---
    in_yaml = False
    all_checked = True
    has_checklist_items = False

    # Use regex to find checklist items
    unchecked_regex = re.compile(r'^\s*-\s*\[\s\]') # Matches '- [ ]'
    checked_regex = re.compile(r'^\s*-\s*\[x\]', re.IGNORECASE) # Matches '- [x]'

    for line in lines:
        if unchecked_regex.search(line):
            all_checked = False
            has_checklist_items = True
        elif checked_regex.search(line):
            has_checklist_items = True

    # A task is only considered 'done' if it has checklist items and they are all checked.
    is_complete = has_checklist_items and all_checked

    # --- Apply Decision Rules ---
    if is_complete:
        # Task is done, update status and move to 'Done' folder
        new_lines = []
        for i, line in enumerate(lines):
            # Find and replace the status line, handling missing status safely.
            if line.strip().startswith('Status:'):
                new_lines.append('Status: done\n')
            else:
                new_lines.append(line)

        done_filepath = os.path.join(DONE_FOLDER, task_filename)

        try:
            # Write the updated content to the new location first
            with open(done_filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # Then remove the original file to complete the "move"
            os.remove(task_filepath)

            print(f"Task '{task_filename}' complete. Moved to '{DONE_FOLDER}'.")
            log_task_processing(task_filename, 'done')
        except (IOError, OSError) as e:
            print(f"Error: Could not move file {task_filename} to {DONE_FOLDER}. Reason: {e}")

    else:
        # Task is not complete, ensure 'Next Actions' section exists
        content = "".join(lines)
        next_actions_header = "## Next Actions"

        if next_actions_header not in content:
            # If the header doesn't exist, append it with a default message.
            # This avoids overwriting any user content.
            next_action_text = (
                "\n"
                f"{next_actions_header}\n"
                "- [ ] Continue working on the checklist items to complete the task.\n"
            )
            try:
                with open(task_filepath, 'a', encoding='utf-8') as f:
                    f.write(next_action_text)
                print(f"Task '{task_filename}' is pending. Added 'Next Actions' section.")
            except IOError as e:
                 print(f"Error: Could not update task file {task_filepath}. Reason: {e}")
        else:
            print(f"Task '{task_filename}' is pending. 'Next Actions' section already exists.")

        log_task_processing(task_filename, 'pending')


def monitor_approved_folder():
    """
    Monitor the Approved folder for new approval files.
    Runs in an infinite loop with sleep intervals.
    Processes any .md files with action_type = linkedin_post.
    """
    print(f"Monitoring {APPROVED_FOLDER} folder for approved tasks...")
    log_approval_execution("monitor", "started", f"Watching {APPROVED_FOLDER}")

    processed_files = set()

    while True:
        try:
            # Check if Approved folder exists
            if not os.path.exists(APPROVED_FOLDER):
                time.sleep(5)
                continue

            # Get all .md files in Approved folder
            approved_files = [
                f for f in os.listdir(APPROVED_FOLDER)
                if f.endswith('.md') and os.path.isfile(os.path.join(APPROVED_FOLDER, f))
            ]

            # Process each approved file
            for approval_filename in approved_files:
                if approval_filename not in processed_files:
                    print(f"Found new approval: {approval_filename}")
                    success = process_approved_task(approval_filename)

                    if success:
                        processed_files.add(approval_filename)
                    else:
                        # Don't add to processed set if failed - may retry later
                        print(f"Approval '{approval_filename}' processing failed, will retry...")

            # Sleep before next check
            time.sleep(5)

        except KeyboardInterrupt:
            print("\nApproved folder monitoring stopped by user")
            log_approval_execution("monitor", "stopped", "User interrupt")
            break
        except Exception as e:
            print(f"Error in approved folder monitor: {e}")
            time.sleep(5)


def main():
    """
    Main function to run the task processing script.
    Processes Needs_Action folder first, then monitors Approved folder continuously.
    """
    print("Ralph loop started successfully")
    print("Starting task processor...")
    ensure_directories_exist()

    # First, process any existing tasks in Needs_Action folder
    try:
        tasks = [f for f in os.listdir(NEEDS_ACTION_FOLDER) if os.path.isfile(os.path.join(NEEDS_ACTION_FOLDER, f))]
    except OSError as e:
        print(f"Error: Could not read directory {NEEDS_ACTION_FOLDER}. Reason: {e}")
        tasks = []

    if tasks:
        print(f"Found {len(tasks)} task(s) to process in Needs_Action folder.")
        for task_filename in tasks:
            process_single_task(task_filename)
    else:
        print("No tasks to process in 'Needs_Action' folder.")

    print("Initial task processing complete.")
    print("Starting Approved folder monitor (infinite loop)...")

    # Start monitoring Approved folder (infinite loop with sleep)
    monitor_approved_folder()


if __name__ == "__main__":
    main()
