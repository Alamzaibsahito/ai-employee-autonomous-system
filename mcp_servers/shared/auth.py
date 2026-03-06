"""
Shared Authentication Module for MCP Servers

This module provides centralized credential management and authentication
utilities for all MCP servers. It loads credentials from environment
variables and provides validation functions.

IMPORTANT: Never hardcode credentials. Always use environment variables.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Centralized credential manager for MCP servers.
    
    All credentials are loaded from environment variables.
    This class provides methods to safely access and validate credentials.
    """
    
    def __init__(self):
        self._credentials_loaded = False
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load all credentials from environment variables."""
        try:
            # Gmail credentials
            self.gmail_client_id = os.getenv('GMAIL_CLIENT_ID')
            self.gmail_client_secret = os.getenv('GMAIL_CLIENT_SECRET')
            self.gmail_refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
            self.gmail_email_address = os.getenv('GMAIL_EMAIL_ADDRESS')
            
            # LinkedIn credentials
            self.linkedin_client_id = os.getenv('LINKEDIN_CLIENT_ID')
            self.linkedin_client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
            self.linkedin_access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
            self.linkedin_organization_id = os.getenv('LINKEDIN_ORGANIZATION_ID')
            
            # MCP Server configuration
            self.gmail_mcp_host = os.getenv('GMAIL_MCP_HOST', '127.0.0.1')
            self.gmail_mcp_port = int(os.getenv('GMAIL_MCP_PORT', '8001'))
            self.linkedin_mcp_host = os.getenv('LINKEDIN_MCP_HOST', '127.0.0.1')
            self.linkedin_mcp_port = int(os.getenv('LINKEDIN_MCP_PORT', '8002'))
            
            self._credentials_loaded = True
            logger.info("Credentials loaded from environment variables")
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            self._credentials_loaded = False
    
    def validate_gmail_credentials(self) -> tuple[bool, str]:
        """
        Validate Gmail credentials are present.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        missing = []
        
        if not self.gmail_client_id:
            missing.append('GMAIL_CLIENT_ID')
        if not self.gmail_client_secret:
            missing.append('GMAIL_CLIENT_SECRET')
        if not self.gmail_refresh_token:
            missing.append('GMAIL_REFRESH_TOKEN')
        if not self.gmail_email_address:
            missing.append('GMAIL_EMAIL_ADDRESS')
        
        if missing:
            error_msg = f"Missing Gmail credentials: {', '.join(missing)}"
            logger.warning(error_msg)
            return False, error_msg
        
        return True, "Gmail credentials validated"
    
    def validate_linkedin_credentials(self) -> tuple[bool, str]:
        """
        Validate LinkedIn credentials are present.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        missing = []
        
        if not self.linkedin_client_id:
            missing.append('LINKEDIN_CLIENT_ID')
        if not self.linkedin_client_secret:
            missing.append('LINKEDIN_CLIENT_SECRET')
        if not self.linkedin_access_token:
            missing.append('LINKEDIN_ACCESS_TOKEN')
        
        if missing:
            error_msg = f"Missing LinkedIn credentials: {', '.join(missing)}"
            logger.warning(error_msg)
            return False, error_msg
        
        return True, "LinkedIn credentials validated"
    
    def get_gmail_config(self) -> Dict[str, Any]:
        """Get Gmail configuration dictionary."""
        return {
            'client_id': self.gmail_client_id,
            'client_secret': self.gmail_client_secret,
            'refresh_token': self.gmail_refresh_token,
            'email_address': self.gmail_email_address,
        }
    
    def get_linkedin_config(self) -> Dict[str, Any]:
        """Get LinkedIn configuration dictionary."""
        return {
            'client_id': self.linkedin_client_id,
            'client_secret': self.linkedin_client_secret,
            'access_token': self.linkedin_access_token,
            'organization_id': self.linkedin_organization_id,
        }
    
    def get_mcp_server_urls(self) -> Dict[str, str]:
        """Get MCP server URLs."""
        return {
            'gmail': f"http://{self.gmail_mcp_host}:{self.gmail_mcp_port}",
            'linkedin': f"http://{self.linkedin_mcp_host}:{self.linkedin_mcp_port}",
        }


class ActionLogger:
    """
    Centralized action logger for MCP servers.
    
    Logs every action performed by MCP servers for audit purposes.
    """
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.logger = logging.getLogger(f"MCP.{server_name}")
    
    def log_action(self, action: str, status: str, details: Dict[str, Any]) -> None:
        """
        Log an action performed by the MCP server.
        
        Args:
            action: Name of the action (e.g., 'send_email', 'create_post')
            status: Status of the action ('success', 'error', 'pending')
            details: Additional details about the action
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'server': self.server_name,
            'action': action,
            'status': status,
            'details': details
        }
        
        if status == 'success':
            self.logger.info(f"Action: {action} | Status: {status} | Details: {details}")
        elif status == 'error':
            self.logger.error(f"Action: {action} | Status: {status} | Details: {details}")
        else:
            self.logger.warning(f"Action: {action} | Status: {status} | Details: {details}")
    
    def log_request(self, endpoint: str, method: str, payload: Optional[Dict]) -> None:
        """Log incoming HTTP request."""
        self.logger.info(f"Request: {method} {endpoint} | Payload: {payload}")
    
    def log_response(self, endpoint: str, status_code: int, response: Dict) -> None:
        """Log outgoing HTTP response."""
        self.logger.info(f"Response: {endpoint} | Status: {status_code} | Response: {response}")


# Global credential manager instance
credential_manager = CredentialManager()


def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance."""
    return credential_manager


def create_action_logger(server_name: str) -> ActionLogger:
    """Create an action logger for a specific MCP server."""
    return ActionLogger(server_name)
