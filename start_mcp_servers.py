"""
MCP Servers Startup Script

This script starts all MCP servers for the hackathon project.
Run this to start both Gmail and LinkedIn MCP servers.

Usage:
    python start_mcp_servers.py
    
To start individual servers:
    python mcp_servers/gmail_mcp/server.py
    python mcp_servers/linkedin_mcp/server.py
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# MCP Server configurations
MCP_SERVERS = {
    "gmail": {
        "script": PROJECT_ROOT / "mcp_servers" / "gmail_mcp" / "server.py",
        "host": os.getenv("GMAIL_MCP_HOST", "127.0.0.1"),
        "port": int(os.getenv("GMAIL_MCP_PORT", "8001")),
        "name": "Gmail MCP Server"
    },
    "linkedin": {
        "script": PROJECT_ROOT / "mcp_servers" / "linkedin_mcp" / "server.py",
        "host": os.getenv("LINKEDIN_MCP_HOST", "127.0.0.1"),
        "port": int(os.getenv("LINKEDIN_MCP_PORT", "8002")),
        "name": "LinkedIn MCP Server"
    },
    "odoo": {
        "script": PROJECT_ROOT / "mcp_servers" / "odoo_mcp" / "server.py",
        "host": os.getenv("ODOO_MCP_HOST", "127.0.0.1"),
        "port": int(os.getenv("ODOO_MCP_PORT", "8003")),
        "name": "Odoo MCP Server"
    }
}


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = PROJECT_ROOT / ".env"
    
    if not env_file.exists():
        print("WARNING: .env file not found!")
        print("Please create .env file with required credentials.")
        return False
    
    # Check for placeholder values
    with open(env_file, 'r') as f:
        content = f.read()
    
    warnings = []
    if "your_gmail_client_id_here" in content:
        warnings.append("GMAIL_CLIENT_ID not configured")
    if "your_linkedin_client_id_here" in content:
        warnings.append("LINKEDIN_CLIENT_ID not configured")
    
    if warnings:
        print("\nWARNING: Some credentials are not configured:")
        for warning in warnings:
            print(f"  - {warning}")
        print("\nServers will start but may return 'credentials not configured' errors.\n")
    
    return True


def start_server(server_key, server_config):
    """Start a single MCP server."""
    print(f"Starting {server_config['name']}...")
    print(f"  URL: http://{server_config['host']}:{server_config['port']}")
    print(f"  Script: {server_config['script']}")
    
    cmd = [sys.executable, str(server_config['script'])]
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT
        )
        return process
    except Exception as e:
        print(f"ERROR: Failed to start {server_config['name']}: {e}")
        return None


def main():
    """Main function to start all MCP servers."""
    print("=" * 60)
    print("MCP Servers Startup")
    print("=" * 60)
    print()
    
    # Check environment
    check_env_file()
    
    # Start servers
    processes = []
    
    print("\nStarting MCP servers...\n")
    
    for server_key, server_config in MCP_SERVERS.items():
        process = start_server(server_key, server_config)
        if process:
            processes.append((server_key, process))
            time.sleep(1)  # Stagger startup
    
    print("\n" + "=" * 60)
    print("All MCP servers started!")
    print("=" * 60)
    print("\nServer URLs:")
    for server_key, server_config in MCP_SERVERS.items():
        print(f"  {server_config['name']}: http://{server_config['host']}:{server_config['port']}")
    
    print("\nHealth check endpoints:")
    for server_key, server_config in MCP_SERVERS.items():
        print(f"  {server_config['name']}: http://{server_config['host']}:{server_config['port']}/health")
    
    print("\nPress Ctrl+C to stop all servers")
    print("=" * 60)
    
    # Wait for all processes
    try:
        for server_key, process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down MCP servers...")
        for server_key, process in processes:
            process.terminate()
        print("All servers stopped.")


if __name__ == "__main__":
    main()
