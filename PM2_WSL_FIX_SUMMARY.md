# PM2 + WSL Process Tasks Fix Summary

## Problem
PM2 was unable to import Python site modules when running `process_tasks.py` under WSL, causing:
```
Fatal Python error: init_import_site
```

## Root Cause
The issue occurred because:
1. PM2 was calling `python3` directly without activating the virtual environment
2. WSL environment has different Python path resolution than native Windows
3. Missing proper environment variables for Python execution under PM2

## Solution Applied

### 1. Updated `process_tasks.py`
- Added startup log message: `"Ralph loop started successfully"`
- Verified proper `if __name__ == "__main__": main()` wrapper exists
- No relative `sys.path` modifications present (already clean)

### 2. Updated `ecosystem.config.js`
Changed the `process_tasks` app configuration:
```javascript
{
  name: 'process_tasks',
  script: './process_tasks.py',
  interpreter: 'python',        // Changed from 'python3'
  interpreter_args: '-u',       // Added unbuffered output
  env: {
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',  // Added for proper encoding
  },
}
```

### 3. Created Startup Wrappers

#### For WSL/Linux: `start_process_tasks.sh`
- Activates virtual environment automatically
- Clears `PYTHONHOME` and `PYTHONPATH` to prevent conflicts
- Uses the correct Python from venv

#### For Windows: `start_process_tasks.bat`
- Same functionality for Windows PM2
- Cross-platform compatibility

## Usage

### Option 1: Direct PM2 Start (Recommended)
```bash
# In WSL
pm2 start ecosystem.config.js --only process_tasks

# Or with the wrapper script
pm2 start start_process_tasks.sh --name process_tasks
```

### Option 2: Manual Testing
```bash
# WSL
./start_process_tasks.sh

# Windows
start_process_tasks.bat
```

## Verification

After starting PM2, verify with:
```bash
pm2 logs process_tasks
pm2 status
```

You should see:
```
Ralph loop started successfully
Starting task processor...
```

## Files Modified
1. `process_tasks.py` - Added startup log message
2. `ecosystem.config.js` - Updated interpreter and environment variables

## Files Created
1. `start_process_tasks.sh` - WSL/Linux startup wrapper
2. `start_process_tasks.bat` - Windows startup wrapper
3. `PM2_WSL_FIX_SUMMARY.md` - This documentation

## No Changes To
- WhatsApp MCP logic
- LinkedIn MCP logic
- Any other MCP server configurations
