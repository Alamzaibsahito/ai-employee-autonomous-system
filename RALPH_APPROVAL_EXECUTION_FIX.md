# Ralph Task Processor - Approved Folder Execution Fix

## Problem
Ralph loop only scanned the `Needs_Action` folder. After manual approval, files moved to `Approved/` were never executed.

## Solution
Modified `process_tasks.py` to monitor the `Approved/` folder and execute approved LinkedIn post tasks.

## Expected Flow
```
Needs_Action → Approved → Executed → Completed
```

## Changes Made

### 1. New Configuration
Added new folder constants:
```python
APPROVED_FOLDER = "Approved"
COMPLETED_FOLDER = "Completed"
```

### 2. YAML Frontmatter Parser
Added `parse_yaml_frontmatter()` function to extract metadata from approval files:
- Parses `action_type` from YAML frontmatter
- Detects `linkedin_post` action type

### 3. Post Content Extractor
Added `extract_post_content()` function:
- Extracts post text from "## Proposed Content" section
- Extracts hashtags from "## Hashtags" section
- Returns structured post data for LinkedIn API

### 4. LinkedIn Post Executor
Added `execute_linkedin_post()` function:
- Sends HTTP POST request to LinkedIn MCP server
- Uses `/create_post` endpoint
- Includes `X-Approval-Status: approved` header
- Returns success/failure status with post ID

### 5. Approved Task Processor
Added `process_approved_task()` function:
- Reads approval file from `Approved/` folder
- Parses YAML frontmatter
- Detects `action_type = linkedin_post`
- Executes LinkedIn post
- Moves file to `Completed/` on success

### 6. Infinite Loop Monitor
Added `monitor_approved_folder()` function:
- Runs in infinite `while True` loop
- Uses `time.sleep(5)` between checks
- Tracks processed files to avoid duplicates
- Handles KeyboardInterrupt gracefully

### 7. Updated Main Function
Modified `main()` to:
1. Process existing `Needs_Action` tasks first
2. Start `monitor_approved_folder()` infinite loop

### 8. Required Log Messages
Added these log messages:
- `"Approved task detected"` - When new approval found
- `"Executing LinkedIn approval task"` - Before execution
- `"LinkedIn post successful"` - On successful post

## Log Output Example
```
Ralph loop started successfully
Starting task processor...
Found 2 task(s) to process in Needs_Action folder.
Task 'task_1.md' complete. Moved to 'Done'.
Initial task processing complete.
Starting Approved folder monitor (infinite loop)...
Monitoring Approved folder for approved tasks...
Found new approval: approval_20260301073831_999bb7cf.md
Approved task detected
Executing LinkedIn approval task
LinkedIn post successful
Approval 'approval_20260301073831_999bb7cf.md' moved to 'Completed'
```

## Usage

### Start with PM2
```bash
pm2 start ecosystem.config.js --only process_tasks
```

### Manual Start
```bash
python process_tasks.py
```

## Files Modified
1. `process_tasks.py` - Complete rewrite with approval monitoring

## Files NOT Modified (as required)
- LinkedIn MCP server (`mcp_servers/linkedin_mcp/server.py`)
- Approval creation logic
- WhatsApp MCP logic

## Dependencies
Already available in `requirements.txt`:
- `requests>=2.31.0` - HTTP client for LinkedIn API
- `pyyaml>=6.0.1` - YAML frontmatter parsing

## Configuration
Environment variables (optional):
```bash
LINKEDIN_MCP_HOST=127.0.0.1  # Default
LINKEDIN_MCP_PORT=8002       # Default
```

## Error Handling
- Connection errors to LinkedIn MCP server are caught and logged
- Failed approvals remain in `Approved/` for retry
- All errors logged to `Logs/System_Log.md`
