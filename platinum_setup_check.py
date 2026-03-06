#!/usr/bin/env python3
"""
============================================================
Platinum Tier - Setup Verification Script
============================================================
Run this to verify all Platinum tier components are in place.

Usage:
    python platinum_setup_check.py
============================================================
"""

import os
import sys
from pathlib import Path

# Colors for output
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color

# Use ASCII-safe symbols for Windows compatibility
CHECK_PASS = "[OK]"
CHECK_FAIL = "[FAIL]"
CHECK_WARN = "[WARN]"

def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = f"{GREEN}{CHECK_PASS}{NC}" if exists else f"{RED}{CHECK_FAIL}{NC}"
    print(f"  {status} {description}: {path}")
    return exists

def check_directory(path: str, description: str) -> bool:
    """Check if a directory exists."""
    exists = os.path.isdir(path)
    status = f"{GREEN}{CHECK_PASS}{NC}" if exists else f"{RED}{CHECK_FAIL}{NC}"
    print(f"  {status} {description}: {path}")
    return exists

def check_executable(path: str, description: str) -> bool:
    """Check if a file exists and is executable."""
    exists = os.path.exists(path)
    executable = exists and os.access(path, os.X_OK)
    
    if not exists:
        status = f"{RED}{CHECK_FAIL}{NC}"
        print(f"  {status} {description}: {path} (NOT FOUND)")
        return False
    
    if executable:
        status = f"{GREEN}{CHECK_PASS}{NC}"
        print(f"  {status} {description}: {path} (executable)")
        return True
    else:
        status = f"{YELLOW}{CHECK_WARN}{NC}"
        print(f"  {status} {description}: {path} (not executable - run: chmod +x {path})")
        return True  # Still passes, but with warning

def main():
    print("=" * 60)
    print("       Platinum Tier Setup Verification")
    print("=" * 60)
    print()
    
    checks = []
    
    # 1. Core Scripts
    print("1. Core Startup Scripts")
    checks.append(check_file("start_all.sh", "Startup script"))
    checks.append(check_file("ecosystem.config.js", "PM2 config"))
    print()
    
    # 2. Platinum Modules
    print("2. Platinum Tier Modules")
    checks.append(check_file("platinum/__init__.py", "Platinum module"))
    checks.append(check_file("platinum/health_monitor.py", "Health monitor"))
    checks.append(check_file("platinum/work_zone.py", "Work-zone specialization"))
    print()
    
    # 3. Social Media MCP Servers
    print("3. Social Media MCP Servers")
    checks.append(check_file("mcp_servers/social_mcp/twitter_server.py", "Twitter MCP"))
    checks.append(check_file("mcp_servers/social_mcp/facebook_server.py", "Facebook MCP"))
    checks.append(check_file("mcp_servers/social_mcp/instagram_server.py", "Instagram MCP"))
    print()
    
    # 4. Sync Scripts
    print("4. Vault Sync Scripts")
    checks.append(check_file("scripts/sync.sh", "Sync script"))
    checks.append(check_file("scripts/cron_setup.txt", "Cron templates"))
    print()
    
    # 5. Work Zone Folders
    print("5. Work Zone Folders")
    checks.append(check_directory("AI_Employee_Vault/Vault", "Cloud workspace"))
    checks.append(check_directory("AI_Employee_Vault/Needs_Action", "Task queue"))
    checks.append(check_directory("AI_Employee_Vault/Pending_Approval", "Approval queue"))
    checks.append(check_directory("AI_Employee_Vault/In_Progress", "Local workspace"))
    checks.append(check_directory("AI_Employee_Vault/Updates", "Alerts folder"))
    print()
    
    # 6. Log Folders
    print("6. Log Folders")
    checks.append(check_directory("Logs/central", "Central logs"))
    checks.append(check_directory("Logs/Archive", "Log archive"))
    print()
    
    # 7. Security Files
    print("7. Security Configuration")
    checks.append(check_file(".gitignore", "Git ignore rules"))
    print()
    
    # 8. Documentation
    print("8. Documentation")
    checks.append(check_file("PLATINUM_TIER_SUMMARY.md", "Platinum summary"))
    checks.append(check_file("QUICK_REFERENCE.md", "Quick reference"))
    print()
    
    # Summary
    print("=" * 60)
    total = len(checks)
    passed = sum(checks)
    failed = total - passed
    
    if failed == 0:
        print(f"{GREEN}All checks passed! ({passed}/{total}){NC}")
        print()
        print("Platinum Tier is ready for deployment!")
        print()
        print("Next steps:")
        print("  1. Configure .env with your credentials")
        print("  2. Run: ./start_all.sh start")
        print("  3. Setup vault sync: ./scripts/sync.sh init")
        print("  4. Configure cron: crontab scripts/cron_setup.txt")
        return 0
    else:
        print(f"{RED}Some checks failed! ({passed}/{total} passed){NC}")
        print()
        print("Missing components:")
        
        # List failed checks
        failed_items = [
            "Core Scripts" if not checks[0] or not checks[1] else None,
            "Platinum Modules" if not checks[2] or not checks[3] or not checks[4] else None,
            "Social MCP Servers" if not checks[5] or not checks[6] or not checks[7] else None,
            "Sync Scripts" if not checks[8] or not checks[9] else None,
            "Work Zone Folders" if not all(checks[10:15]) else None,
            "Log Folders" if not checks[15] or not checks[16] else None,
            "Security Files" if not checks[17] else None,
            "Documentation" if not checks[18] or not checks[19] else None,
        ]
        
        for item in failed_items:
            if item:
                print(f"  - {item}")
        
        print()
        print("Run the setup again or check for missing files.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
