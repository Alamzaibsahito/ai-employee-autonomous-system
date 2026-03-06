# WhatsApp Watcher MCP Skill

A production-ready WhatsApp message monitoring skill for the AI Employee system. This watcher listens for incoming WhatsApp messages and routes them to the AI Employee Vault for processing.

## Features

- 📱 **QR Code Authentication** - Scan to authenticate on first run
- 💾 **Session Persistence** - Local session storage (never synced to cloud)
- 📨 **Message Capture** - Captures all incoming messages with metadata
- 📁 **Vault Integration** - Writes messages to `AI_Employee_Vault/Needs_Action/whatsapp/`
- 📝 **Centralized Logging** - Logs events to `Logs/central/whatsapp.log`
- 🔄 **Auto-Reconnect** - Automatic reconnection with configurable attempts
- 🛡️ **Security First** - Sessions stored locally only, gitignored
- 🎯 **Orchestrator Compatible** - Runs as background watcher service

## Installation

### Prerequisites

- Node.js >= 16.0.0
- npm or yarn
- WhatsApp mobile app (for QR authentication)

### Install Dependencies

```bash
cd skills/whatsapp-watcher
npm install
```

## Configuration

Configure via environment variables (create a `.env` file or set system variables):

| Variable | Default | Description |
|----------|---------|-------------|
| `WHATSAPP_BASE_DIR` | `..` | Base directory for the skill |
| `WHATSAPP_SESSION_PATH` | `./sessions` | Local session storage path |
| `WHATSAPP_VAULT_PATH` | `../../../AI_Employee_Vault/Needs_Action/whatsapp` | Message output path |
| `WHATSAPP_LOG_PATH` | `../../../Logs/central` | Log file directory |
| `WHATSAPP_LOG_LEVEL` | `info` | Log level (debug, info, warn, error) |
| `WHATSAPP_MESSAGE_PREFIX` | `msg` | Filename prefix for saved messages |
| `WHATSAPP_SESSION_NAME` | `whatsapp-session` | Session client ID |
| `WHATSAPP_RECONNECT_DELAY` | `5000` | Reconnect delay in ms |
| `WHATSAPP_MAX_RECONNECT_ATTEMPTS` | `10` | Max reconnection attempts |
| `WHATSAPP_SECURE_MODE` | `true` | Enable security features |
| `WHATSAPP_SEND_ACK` | `false` | Send acknowledgment messages |

### Example `.env` File

```env
WHATSAPP_LOG_LEVEL=info
WHATSAPP_SEND_ACK=false
WHATSAPP_RECONNECT_DELAY=5000
WHATSAPP_MAX_RECONNECT_ATTEMPTS=10
```

## Usage

### Development Mode

```bash
npm start
```

### Watch Mode (Development)

```bash
npm run dev
```

### Production Mode with PM2

```bash
# Install PM2 globally if not already installed
npm install -g pm2

# Start the WhatsApp watcher
pm2 start scripts/whatsapp_watcher.js --name whatsapp-watcher

# Or using ecosystem file
pm2 start ecosystem.config.js

# View logs
pm2 logs whatsapp-watcher

# Monitor status
pm2 monit

# Restart if needed
pm2 restart whatsapp-watcher

# Stop the service
pm2 stop whatsapp-watcher
```

### PM2 Ecosystem Configuration

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'whatsapp-watcher',
    script: './scripts/whatsapp_watcher.js',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      WHATSAPP_LOG_LEVEL: 'info',
      WHATSAPP_SECURE_MODE: 'true'
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true
  }]
};
```

## First Run - Authentication

1. Start the watcher: `npm start`
2. A QR code will be displayed in the console
3. Open WhatsApp on your phone
4. Go to **Settings** → **Linked Devices** → **Link a Device**
5. Scan the QR code
6. Session will be saved locally for future runs

## Output Structure

### Messages Vault

Messages are saved as JSON files in `AI_Employee_Vault/Needs_Action/whatsapp/`:

```json
{
  "id": "true_1234567890@c.us_ABC123DEF456",
  "timestamp": 1709012345,
  "receivedAt": "2024-02-27T10:30:45.123Z",
  "from": "1234567890@c.us",
  "fromName": "John Doe",
  "contactName": "John Doe",
  "body": "Hello, I need help with my order",
  "type": "chat",
  "hasMedia": false,
  "isGroup": false,
  "groupId": null,
  "replyTo": null,
  "mentions": []
}
```

### Log File

Logs are written to `Logs/central/whatsapp.log` in JSON format with timestamps.

## Security

- ✅ Sessions stored **locally only** in `skills/whatsapp-watcher/sessions/`
- ✅ Session folder added to `.gitignore` - never committed to version control
- ✅ No cloud sync of authentication data
- ✅ Secure mode enabled by default

## Integration with Orchestrator

The WhatsApp Watcher is designed to work with the existing AI Employee orchestrator:

```javascript
// Import in orchestrator
const whatsappWatcher = require('./skills/whatsapp-watcher/scripts/whatsapp_watcher');

// Check health status
const health = whatsappWatcher.getHealthStatus();
console.log(health);
// { service: 'whatsapp-watcher', status: 'running', authenticated: true, ... }
```

## Troubleshooting

### QR Code Not Appearing

- Ensure puppeteer dependencies are installed
- Check if port 3000+ is available
- Try running with `WHATSAPP_LOG_LEVEL=debug`

### Session Authentication Failed

- Delete the session folder: `rm -rf sessions/`
- Restart the watcher to generate new QR code
- Ensure WhatsApp mobile app is connected to internet

### Messages Not Being Saved

- Check vault directory permissions
- Verify `WHATSAPP_VAULT_PATH` is correct
- Check logs for error messages

### High Memory Usage

- Reduce `max_memory_restart` in PM2 config
- Ensure old sessions are cleaned periodically
- Check for message backlog in vault

## File Structure

```
skills/whatsapp-watcher/
├── scripts/
│   └── whatsapp_watcher.js    # Main watcher script
├── sessions/                   # Local session storage (gitignored)
├── package.json               # Dependencies and scripts
├── README.md                  # This file
└── .env                       # Environment variables (optional, gitignored)
```

## License

MIT - AI Employee System
