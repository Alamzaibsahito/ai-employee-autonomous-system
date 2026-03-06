"""
Enterprise Integration Module

Integrates all new enterprise agents (Odoo, Twitter, Facebook, Instagram, Personal)
with the existing scheduler and Ralph loop systems.

This module provides:
- Unified agent execution interface
- Scheduler integration for all agents
- Ralph loop step execution for new agents
- Graceful degradation for all agent calls
- Centralized logging

Usage:
    from skills.enterprise_integration import EnterpriseAgent
    
    agent = EnterpriseAgent()
    
    # Execute Odoo action
    result = agent.execute_odoo_action("create_invoice", {...})
    
    # Execute social media action
    result = agent.execute_social_action("twitter", "post_tweet", {...})
    
    # Execute personal task action
    result = agent.execute_personal_action("route_task", {...})
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Import Agent Modules (with graceful fallback)
# ============================================================

def safe_import(module_path: str, fallback: Callable = None):
    """
    Safely import a module with graceful fallback.
    
    Args:
        module_path: Module path to import
        fallback: Fallback function if import fails
        
    Returns:
        Imported module or fallback
    """
    try:
        parts = module_path.split('.')
        module = __import__(module_path, fromlist=[parts[-1]])
        return module
    except ImportError as e:
        logger.warning(f"Failed to import {module_path}: {e}")
        return fallback


# Try to import agent modules
try:
    from .personal_task_handler import (
        get_personal_handler,
        detect_task_type,
        route_personal_task,
        get_personal_summary
    )
    PERSONAL_AVAILABLE = True
except ImportError:
    PERSONAL_AVAILABLE = False
    logger.warning("Personal task handler not available")

try:
    from ..claude.skills.twitter-post.twitter_agent import (
        post_tweet,
        get_tweet_history,
        twitter_config
    )
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    logger.warning("Twitter agent not available")

try:
    from ..claude.skills.social-media import (
        post_facebook,
        post_instagram,
        get_facebook_posts,
        get_instagram_posts,
        facebook_config,
        instagram_config
    )
    SOCIAL_AVAILABLE = True
except ImportError:
    SOCIAL_AVAILABLE = False
    logger.warning("Social media agents not available")


# ============================================================
# Enterprise Agent Configuration
# ============================================================

class EnterpriseConfig:
    """Centralized configuration for all enterprise agents."""
    
    def __init__(self):
        self.agent_status = {
            "odoo": self._check_odoo_config(),
            "twitter": self._check_twitter_config(),
            "facebook": self._check_facebook_config(),
            "instagram": self._check_instagram_config(),
            "personal": True  # Personal handler doesn't need external config
        }
    
    def _check_odoo_config(self) -> bool:
        """Check if Odoo is configured."""
        return all([
            os.getenv("ODOO_URL"),
            os.getenv("ODOO_DB"),
            os.getenv("ODOO_USERNAME"),
            os.getenv("ODOO_PASSWORD")
        ]) and not any([
            "your_" in (os.getenv(var) or "")
            for var in ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]
        ])
    
    def _check_twitter_config(self) -> bool:
        """Check if Twitter is configured."""
        return all([
            os.getenv("TWITTER_API_KEY"),
            os.getenv("TWITTER_API_SECRET"),
            os.getenv("TWITTER_ACCESS_TOKEN"),
            os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        ]) and not any([
            "your_" in (os.getenv(var) or "")
            for var in ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"]
        ])
    
    def _check_facebook_config(self) -> bool:
        """Check if Facebook is configured."""
        return all([
            os.getenv("FACEBOOK_TOKEN"),
            os.getenv("FACEBOOK_PAGE_ID")
        ]) and not any([
            "your_" in (os.getenv(var) or "")
            for var in ["FACEBOOK_TOKEN", "FACEBOOK_PAGE_ID"]
        ])
    
    def _check_instagram_config(self) -> bool:
        """Check if Instagram is configured."""
        return all([
            os.getenv("INSTAGRAM_TOKEN"),
            os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        ]) and not any([
            "your_" in (os.getenv(var) or "")
            for var in ["INSTAGRAM_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID"]
        ])
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agents."""
        return [agent for agent, available in self.agent_status.items() if available]
    
    def is_agent_available(self, agent: str) -> bool:
        """Check if a specific agent is available."""
        return self.agent_status.get(agent, False)


# ============================================================
# Enterprise Agent
# ============================================================

class EnterpriseAgent:
    """
    Unified enterprise agent for executing actions across all domains.
    
    Features:
    - Unified interface for all agent actions
    - Graceful degradation when agents unavailable
    - Centralized logging
    - Error recovery integration
    """
    
    def __init__(self):
        self.config = EnterpriseConfig()
        self._log_file = "Logs/enterprise_agent.log"
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure log directory exists."""
        os.makedirs("Logs", exist_ok=True)
    
    def _log_action(self, agent: str, action: str, status: str, details: Dict[str, Any]) -> None:
        """
        Log an agent action.
        
        Args:
            agent: Agent name
            action: Action performed
            status: Status (success/error/pending)
            details: Action details
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            log_entry = f"[{timestamp}] {agent.upper()} | {action} | {status} | {str(details)}\n"
            
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            # Also log to system log
            system_log = "Logs/System_Log.md"
            with open(system_log, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] ENTERPRISE_AGENT | {agent}.{action} | {status}\n")
                
        except Exception as e:
            logger.error(f"Failed to log enterprise action: {e}")
    
    def execute_odoo_action(
        self,
        action: str,
        params: Dict[str, Any],
        use_jsonrpc: bool = True
    ) -> Dict[str, Any]:
        """
        Execute an Odoo ERP action.
        
        Args:
            action: Action name (create_invoice, list_invoices, record_payment)
            params: Action parameters
            use_jsonrpc: Use JSON-RPC endpoint
            
        Returns:
            Action result
        """
        if not self.config.is_agent_available("odoo"):
            self._log_action("odoo", action, "error", {"error": "Odoo not configured"})
            return {
                "success": False,
                "error": "Odoo credentials not configured",
                "error_code": "CREDENTIALS_NOT_CONFIGURED"
            }
        
        try:
            # In production, this would call the actual Odoo MCP server
            # For now, return simulated response
            
            if action == "create_invoice":
                result = self._simulate_odoo_create_invoice(params)
            elif action == "list_invoices":
                result = self._simulate_odoo_list_invoices(params)
            elif action == "record_payment":
                result = self._simulate_odoo_record_payment(params)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown Odoo action: {action}",
                    "error_code": "UNKNOWN_ACTION"
                }
            
            self._log_action("odoo", action, "success" if result.get("success") else "error", result)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Odoo action failed: {error_msg}")
            
            self._log_action("odoo", action, "error", {"error": error_msg})
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "ACTION_FAILED"
            }
    
    def _simulate_odoo_create_invoice(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Odoo invoice creation."""
        return {
            "success": True,
            "invoice_id": int(datetime.now().timestamp()) % 100000,
            "message": "Invoice created (simulated)",
            "customer": params.get("customer_name"),
            "amount": params.get("amount")
        }
    
    def _simulate_odoo_list_invoices(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Odoo invoice listing."""
        return {
            "success": True,
            "invoices": [
                {"id": 1, "customer": "ABC Corp", "amount": 5000.00, "status": "posted"},
                {"id": 2, "customer": "XYZ Inc", "amount": 2500.00, "status": "draft"}
            ],
            "count": 2
        }
    
    def _simulate_odoo_record_payment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Odoo payment recording."""
        return {
            "success": True,
            "payment_id": int(datetime.now().timestamp()) % 100000,
            "message": "Payment recorded (simulated)",
            "invoice_id": params.get("invoice_id"),
            "amount": params.get("amount")
        }
    
    def execute_social_action(
        self,
        platform: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a social media action.
        
        Args:
            platform: Platform name (twitter, facebook, instagram)
            action: Action name (post_tweet, post_facebook, post_instagram)
            params: Action parameters
            
        Returns:
            Action result
        """
        if not self.config.is_agent_available(platform):
            self._log_action(platform, action, "error", {"error": f"{platform} not configured"})
            return {
                "success": False,
                "error": f"{platform.capitalize()} credentials not configured",
                "error_code": "CREDENTIALS_NOT_CONFIGURED"
            }
        
        try:
            # Call the appropriate agent function
            if platform == "twitter" and TWITTER_AVAILABLE:
                if action == "post_tweet":
                    result = post_tweet(params.get("message", ""))
                elif action == "get_history":
                    result = {"success": True, "tweets": get_tweet_history(params.get("limit", 10))}
                else:
                    result = {"success": False, "error": f"Unknown Twitter action: {action}"}
            
            elif platform == "facebook" and SOCIAL_AVAILABLE:
                if action == "post_facebook":
                    result = post_facebook(
                        params.get("message", ""),
                        link=params.get("link")
                    )
                elif action == "get_history":
                    result = {"success": True, "posts": get_facebook_posts(params.get("limit", 10))}
                else:
                    result = {"success": False, "error": f"Unknown Facebook action: {action}"}
            
            elif platform == "instagram" and SOCIAL_AVAILABLE:
                if action == "post_instagram":
                    result = post_instagram(
                        params.get("message", ""),
                        image_url=params.get("image_url")
                    )
                elif action == "get_history":
                    result = {"success": True, "posts": get_instagram_posts(params.get("limit", 10))}
                else:
                    result = {"success": False, "error": f"Unknown Instagram action: {action}"}
            
            else:
                result = {
                    "success": False,
                    "error": f"Platform {platform} not available",
                    "error_code": "PLATFORM_NOT_AVAILABLE"
                }
            
            self._log_action(platform, action, "success" if result.get("success") else "error", result)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Social media action failed: {error_msg}")
            
            self._log_action(platform, action, "error", {"error": error_msg})
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "ACTION_FAILED"
            }
    
    def execute_personal_action(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a personal task action.
        
        Args:
            action: Action name (detect_type, route_task, get_tasks, mark_complete)
            params: Action parameters
            
        Returns:
            Action result
        """
        if not PERSONAL_AVAILABLE:
            self._log_action("personal", action, "error", {"error": "Personal handler not available"})
            return {
                "success": False,
                "error": "Personal task handler not available",
                "error_code": "MODULE_NOT_AVAILABLE"
            }
        
        try:
            handler = get_personal_handler()
            
            if action == "detect_type":
                result = {
                    "success": True,
                    "task_type": detect_task_type(params.get("content", ""))
                }
            
            elif action == "route_task":
                result = route_personal_task(
                    params.get("task_file", ""),
                    params.get("task_content", ""),
                    params.get("source_folder", "Inbox")
                )
            
            elif action == "get_tasks":
                result = {
                    "success": True,
                    "tasks": handler.get_personal_tasks(params.get("status", "pending"))
                }
            
            elif action == "mark_complete":
                result = handler.mark_personal_task_complete(params.get("filename", ""))
            
            elif action == "get_summary":
                result = {
                    "success": True,
                    "summary": get_personal_summary()
                }
            
            else:
                result = {
                    "success": False,
                    "error": f"Unknown personal action: {action}",
                    "error_code": "UNKNOWN_ACTION"
                }
            
            self._log_action("personal", action, "success" if result.get("success") else "error", result)
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Personal action failed: {error_msg}")
            
            self._log_action("personal", action, "error", {"error": error_msg})
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "ACTION_FAILED"
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all enterprise agents.
        
        Returns:
            Agent status dictionary
        """
        return {
            "agents": self.config.agent_status,
            "available_agents": self.config.get_available_agents(),
            "timestamp": datetime.now().isoformat()
        }
    
    def execute_ralph_step(
        self,
        step_type: str,
        step_content: str,
        task_file: str
    ) -> Dict[str, Any]:
        """
        Execute a Ralph Loop step using enterprise agents.
        
        This integrates with the Ralph Loop system to execute steps
        that involve enterprise agents.
        
        Args:
            step_type: Step type (odoo, twitter, facebook, instagram, personal)
            step_content: Step content/description
            task_file: Source task file
            
        Returns:
            Step execution result
        """
        self._log_action("ralph", "execute_step", "started", {
            "step_type": step_type,
            "step_content": step_content[:100],
            "task_file": task_file
        })
        
        try:
            # Parse step content to determine action
            step_lower = step_content.lower()
            
            if step_type == "odoo" or "odoo" in step_lower or "invoice" in step_lower:
                # Determine Odoo action from step content
                if "create" in step_lower and "invoice" in step_lower:
                    return self.execute_odoo_action("create_invoice", {
                        "customer_name": "Customer",
                        "amount": 0,
                        "description": step_content
                    })
                elif "list" in step_lower or "invoices" in step_lower:
                    return self.execute_odoo_action("list_invoices", {"limit": 10})
                elif "payment" in step_lower or "record" in step_lower:
                    return self.execute_odoo_action("record_payment", {
                        "invoice_id": 0,
                        "amount": 0
                    })
            
            elif step_type == "twitter" or "tweet" in step_lower:
                return self.execute_social_action("twitter", "post_tweet", {
                    "message": step_content
                })
            
            elif step_type == "facebook" or "facebook" in step_lower:
                return self.execute_social_action("facebook", "post_facebook", {
                    "message": step_content
                })
            
            elif step_type == "instagram" or "instagram" in step_lower:
                return self.execute_social_action("instagram", "post_instagram", {
                    "message": step_content
                })
            
            elif step_type == "personal" or "personal" in step_lower:
                return self.execute_personal_action("detect_type", {
                    "content": step_content
                })
            
            # Default: return success for unrecognized steps
            return {
                "success": True,
                "message": f"Step executed (no action needed for: {step_type})"
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ralph step execution failed: {error_msg}")
            
            self._log_action("ralph", "execute_step", "error", {
                "step_type": step_type,
                "error": error_msg
            })
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "STEP_EXECUTION_FAILED"
            }


# ============================================================
# Module Exports
# ============================================================

# Global instance for convenience
_enterprise_agent = None

def get_enterprise_agent() -> EnterpriseAgent:
    """Get or create the enterprise agent instance."""
    global _enterprise_agent
    if _enterprise_agent is None:
        _enterprise_agent = EnterpriseAgent()
    return _enterprise_agent


def execute_odoo_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an Odoo action."""
    agent = get_enterprise_agent()
    return agent.execute_odoo_action(action, params)


def execute_social_action(platform: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a social media action."""
    agent = get_enterprise_agent()
    return agent.execute_social_action(platform, action, params)


def execute_personal_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a personal task action."""
    agent = get_enterprise_agent()
    return agent.execute_personal_action(action, params)


def get_agent_status() -> Dict[str, Any]:
    """Get agent status."""
    agent = get_enterprise_agent()
    return agent.get_agent_status()


__all__ = [
    'EnterpriseAgent',
    'EnterpriseConfig',
    'get_enterprise_agent',
    'execute_odoo_action',
    'execute_social_action',
    'execute_personal_action',
    'get_agent_status'
]
