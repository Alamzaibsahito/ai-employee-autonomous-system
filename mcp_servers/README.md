# MCP Servers for External Actions

This directory contains Model Context Protocol (MCP) servers for external action automation. All external actions (emails, social media posts) are executed via these MCP servers instead of direct scripts.

## Folder Structure

```
mcp_servers/
├── gmail_mcp/
│   └── server.py          # Gmail MCP server
├── linkedin_mcp/
│   └── server.py          # LinkedIn MCP server
└── shared/
    ├── __init__.py
    └── auth.py            # Shared authentication module
```

## Quick Start

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env` (see Configuration section below)

### Starting the Servers

**Start Gmail MCP Server:**
```bash
cd mcp_servers/gmail_mcp
python server.py
```
Or from project root:
```bash
python -m mcp_servers.gmail_mcp.server
```

**Start LinkedIn MCP Server:**
```bash
cd mcp_servers/linkedin_mcp
python server.py
```
Or from project root:
```bash
python -m mcp_servers.linkedin_mcp.server
```

**Start Both Servers (in separate terminals):**
```bash
# Terminal 1 - Gmail MCP
python mcp_servers/gmail_mcp/server.py

# Terminal 2 - LinkedIn MCP
python mcp_servers/linkedin_mcp/server.py
```

## Server Endpoints

### Gmail MCP Server (Port 8001)

| Endpoint | Method | Description | Approval Required |
|----------|--------|-------------|-------------------|
| `/send_email` | POST | Send an email | Yes (for new contacts) |
| `/draft_email` | POST | Create a draft email | No |
| `/read_recent_emails` | POST | Read recent emails | No |
| `/health` | GET | Health check | No |
| `/status` | GET | Server status | No |

### LinkedIn MCP Server (Port 8002)

| Endpoint | Method | Description | Approval Required |
|----------|--------|-------------|-------------------|
| `/create_post` | POST | Create a LinkedIn post | Yes (public posts) |
| `/schedule_post` | POST | Schedule a post | Yes (public posts) |
| `/generate_post_summary` | POST | Generate post summary | No |
| `/health` | GET | Health check | No |
| `/status` | GET | Server status | No |

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# ============================================================
# MCP Server Configuration
# ============================================================

# Gmail MCP Server
GMAIL_MCP_HOST=127.0.0.1
GMAIL_MCP_PORT=8001

# LinkedIn MCP Server
LINKEDIN_MCP_HOST=127.0.0.1
LINKEDIN_MCP_PORT=8002

# ============================================================
# Gmail API Credentials
# ============================================================
# Get these from Google Cloud Console:
# https://console.cloud.google.com/apis/credentials

GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
GMAIL_REFRESH_TOKEN=your_gmail_refresh_token
GMAIL_EMAIL_ADDRESS=your_email@gmail.com

# ============================================================
# LinkedIn API Credentials
# ============================================================
# Get these from LinkedIn Developer Portal:
# https://www.linkedin.com/developers/apps

LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_ORGANIZATION_ID=your_organization_id (optional, for company pages)
```

### Getting API Credentials

#### Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Use OAuth flow to get refresh token

#### LinkedIn API

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Get Client ID and Client Secret
4. Use OAuth 2.0 flow to get access token

## API Usage Examples

### Gmail MCP Server

#### Send Email

```bash
curl -X POST http://127.0.0.1:8001/send_email \
  -H "Content-Type: application/json" \
  -H "X-Approval-Status: approved" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Hello from MCP",
    "body": "This is a test email sent via Gmail MCP Server.",
    "requires_approval": true
  }'
```

**Response (pending approval):**
```json
{
  "success": false,
  "message": "Email requires human approval before sending",
  "requires_approval": true,
  "approval_request_id": "approval_20260218120000_abc123"
}
```

**Response (approved):**
```json
{
  "success": true,
  "message": "Email sent successfully",
  "data": {
    "id": "msg_20260218120000_xyz789",
    "to": "recipient@example.com",
    "subject": "Hello from MCP",
    "status": "sent",
    "timestamp": "2026-02-18T12:00:00"
  }
}
```

#### Create Draft

```bash
curl -X POST http://127.0.0.1:8001/draft_email \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Draft Email",
    "body": "This is a draft."
  }'
```

#### Read Recent Emails

```bash
curl -X POST http://127.0.0.1:8001/read_recent_emails \
  -H "Content-Type: application/json" \
  -d '{
    "max_results": 5,
    "include_body": true
  }'
```

### LinkedIn MCP Server

#### Create Post

```bash
curl -X POST http://127.0.0.1:8002/create_post \
  -H "Content-Type: application/json" \
  -H "X-Approval-Status: approved" \
  -d '{
    "content": {
      "text": "Excited to announce our new product launch! #innovation #tech",
      "title": "Product Launch Announcement",
      "hashtags": ["innovation", "tech"]
    },
    "visibility": "public",
    "requires_approval": true
  }'
```

#### Schedule Post

```bash
curl -X POST http://127.0.0.1:8002/schedule_post \
  -H "Content-Type: application/json" \
  -H "X-Approval-Status: approved" \
  -d '{
    "content": {
      "text": "Join us for our upcoming webinar on AI trends!",
      "title": "Webinar Announcement"
    },
    "scheduled_time": "2026-02-20T14:00:00Z",
    "visibility": "public",
    "timezone": "UTC",
    "requires_approval": true
  }'
```

#### Generate Post Summary

```bash
curl -X POST http://127.0.0.1:8002/generate_post_summary \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Long form content that needs to be summarized for LinkedIn...",
    "max_length": 500,
    "tone": "professional",
    "include_hashtags": true
  }'
```

## Human Approval Workflow

### How Approval Works

1. **Request Received**: MCP server receives a request for a sensitive action (email/public post)
2. **Approval Check**: Server checks `X-Approval-Status` header
3. **Pending**: If not approved, returns `approval_request_id`
4. **Human Review**: User reviews request in `Pending_Approval/` folder
5. **Approval**: User moves file to `Approved/` folder
6. **Retry**: Agent retries request with `X-Approval-Status: approved`

### Integration with Human Approval Skill

The MCP servers integrate with the existing `Human_Approval_Skill.md` workflow:

```
Agent Skill → MCP Server → Check Approval → If pending: create approval request
                                              ↓
                                    Human reviews in Pending_Approval/
                                              ↓
                                    Human moves to Approved/
                                              ↓
Agent Skill → MCP Server → X-Approval-Status: approved → Execute action
```

## Error Handling

### Retry-Safe Behavior

All MCP endpoints are designed to be retry-safe:

- **Idempotent Operations**: Draft creation and summary generation are idempotent
- **Approval Tracking**: Approval request IDs are tracked to prevent duplicates
- **Error Responses**: Structured error responses with error codes

### Error Response Format

```json
{
  "success": false,
  "error": "Failed to send email",
  "error_code": "EMAIL_SEND_FAILED",
  "details": {
    "message": "SMTP connection failed"
  }
}
```

### Common Error Codes

| Error Code | Description | Retry? |
|------------|-------------|--------|
| `CREDENTIALS_NOT_CONFIGURED` | Missing environment variables | No |
| `APPROVAL_REQUIRED` | Action requires human approval | Yes (after approval) |
| `VALIDATION_ERROR` | Invalid request data | No |
| `API_ERROR` | External API failure | Yes |
| `INTERNAL_ERROR` | Server error | Yes |

## Logging

All actions are logged for audit purposes:

- **Request Logging**: Every incoming request is logged
- **Action Logging**: Every action (success/error/pending) is logged
- **Response Logging**: Every response is logged

Logs are written to the console and can be configured to write to files.

### Log Format

```
2026-02-18 12:00:00 - MCP.gmail - INFO - Action: send_email | Status: success | Details: {"to": "user@example.com", "message_id": "msg_123"}
```

## Integration with Agent Skills

Agent skills should call MCP servers instead of executing external actions directly:

```python
import requests

def send_email_via_mcp(to, subject, body, approval_status=None):
    """Send email via Gmail MCP server."""
    url = "http://127.0.0.1:8001/send_email"
    headers = {"Content-Type": "application/json"}
    
    if approval_status:
        headers["X-Approval-Status"] = approval_status
    
    payload = {
        "to": to,
        "subject": subject,
        "body": body,
        "requires_approval": True
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
```

## Health Checks

Check server health:

```bash
# Gmail MCP
curl http://127.0.0.1:8001/health

# LinkedIn MCP
curl http://127.0.0.1:8002/health
```

**Response:**
```json
{
  "status": "healthy",
  "server": "gmail_mcp",
  "timestamp": "2026-02-18T12:00:00",
  "credentials_configured": true
}
```

## Troubleshooting

### Server Won't Start

1. Check if port is already in use:
   ```bash
   netstat -ano | findstr :8001
   ```

2. Check environment variables are set correctly

3. Check dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

### Credentials Error

- Verify all required environment variables are set in `.env`
- Check credentials are valid (not expired)
- For Gmail, ensure OAuth consent screen is configured

### Approval Not Working

- Verify `X-Approval-Status` header is set to `approved`
- Check approval request was created in `Pending_Approval/`
- Verify human moved file to `Approved/` folder

## Security Notes

- **Never hardcode credentials** - Always use environment variables
- **Use HTTPS in production** - Currently HTTP for local development
- **Rotate credentials regularly** - Especially access tokens
- **Limit MCP server access** - Bind to localhost (127.0.0.1) only
- **Audit logs regularly** - Review `Logs/System_Log.md` for suspicious activity

## Related Files

- `Human_Approval_Skill.md` - Human-in-the-Loop approval workflow
- `Security_Secrets_Management_Skill.md` - Secrets management guidelines
- `.env` - Environment variables configuration
- `requirements.txt` - Python dependencies
