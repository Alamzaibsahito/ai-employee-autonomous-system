# AI Employee Dashboard

A professional AI Employee Monitoring Dashboard similar to a modern DevOps control panel.

## Features

- **Real-time Statistics**: Inbox count, Needs Action, Pending Approval, Done, Errors
- **System Daemon Monitoring**: Track orchestrator, vault-watcher, gmail-watcher, watchdog, bank-watcher, whatsapp-watcher
- **Recent Tasks Table**: View recent tasks with intent, confidence, status, and modified time
- **Pending Approval Panel**: Right-side panel showing approval status
- **Auto Refresh**: Dashboard auto-refreshes every 5 seconds
- **DRY RUN Mode**: Toggle dry run mode for safe testing
- **Glass Dark UI**: Modern glassmorphism design with neon accents

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+ with the following packages:
  - fastapi
  - uvicorn
  - pydantic
  - psutil

## Quick Start

### 1. Start the Backend API Server

```bash
# Navigate to the bronze directory
cd C:\hackathon-0\bronze

# Start the dashboard API
python dashboard_api.py
```

The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

### 2. Install Frontend Dependencies

```bash
# Navigate to dashboard_ui directory
cd C:\hackathon-0\bronze\dashboard_ui

# Install dependencies
npm install
```

### 3. Start the Development Server

```bash
# Still in dashboard_ui directory
npm run dev
```

The dashboard will open automatically at: http://localhost:5173

## Project Structure

```
dashboard_ui/
├── src/
│   ├── components/
│   │   ├── Header.jsx              # Top header with title, refresh, dry run toggle
│   │   ├── StatsRow.jsx            # Statistics cards row
│   │   ├── SystemDaemons.jsx       # Daemon status grid
│   │   ├── RecentTasksTable.jsx    # Recent tasks table
│   │   └── PendingApprovalPanel.jsx # Pending approvals side panel
│   ├── services/
│   │   └── api.js                  # API service layer
│   ├── App.jsx                     # Main app component
│   ├── main.jsx                    # React entry point
│   └── index.css                   # Global styles
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── vite.config.js
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/stats` | GET | Dashboard statistics |
| `/api/daemons` | GET | System daemon status |
| `/api/tasks/recent` | GET | Recent tasks |
| `/api/approvals/pending` | GET | Pending approvals |
| `/api/dashboard` | GET | Complete dashboard data |
| `/api/folders` | GET | Folder information |

## Tech Stack

### Frontend
- **React 18** - UI library
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Axios** - HTTP client

### Backend
- **FastAPI** - API framework
- **Uvicorn** - ASGI server
- **Psutil** - Process monitoring

## UI Design

### Color Scheme
- **Background**: Dark gradient (#0a0a0f to #12121a)
- **Cards**: Glass effect with blur
- **Accents**: Neon green (#00ff88), Neon blue (#00d4ff), Neon purple (#bf00ff)

### Status Indicators
- **ONLINE**: Neon green badge with pulse animation
- **OFFLINE**: Red badge

### Animations
- Smooth transitions on hover
- Pulse animation for status indicators
- Spin animation for refresh button
- Auto-refresh every 5 seconds

## Troubleshooting

### Dashboard not loading data
1. Ensure the backend API is running: `python dashboard_api.py`
2. Check if port 8000 is available
3. Verify CORS is enabled in the backend

### Frontend not starting
1. Run `npm install` to install dependencies
2. Check if port 5173 is available
3. Clear node_modules and reinstall: `rm -rf node_modules && npm install`

### API connection errors
1. Verify backend is running on http://localhost:8000
2. Check browser console for CORS errors
3. Ensure proxy configuration in vite.config.js is correct

## Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## License

Internal use only - AI Employee Hackathon Project
