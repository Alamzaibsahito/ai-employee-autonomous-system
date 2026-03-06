"""
Error Recovery Wrappers for Existing Components

This module provides wrapper functions that can be used to wrap
existing component functions without modifying their original code.

Usage:
    from skills.error_recovery_wrapper import wrap_watcher, wrap_task_processor
    
    # Wrap existing functions
    safe_monitor_inbox = wrap_watcher(file_watcher.monitor_inbox)
    safe_process_task = wrap_task_processor(process_tasks.process_task)
"""

import os
import logging
from datetime import datetime
from typing import Callable, Any, Dict, Optional

# Import error recovery components
try:
    from .error_recovery import (
        ErrorRecovery,
        handle_error_gracefully,
        safe_watcher_operation,
        safe_task_processing,
        safe_mcp_call,
        safe_accounting_update,
        safe_report_generation,
        get_system_health,
    )
except ImportError:
    from error_recovery import (
        ErrorRecovery,
        handle_error_gracefully,
        safe_watcher_operation,
        safe_task_processing,
        safe_mcp_call,
        safe_accounting_update,
        safe_report_generation,
        get_system_health,
    )

logger = logging.getLogger(__name__)

# Ensure Logs directory exists
os.makedirs("Logs", exist_ok=True)


# ============================================================
# Watcher Wrappers
# ============================================================

def wrap_watcher(func: Callable) -> Callable:
    """
    Wrap a watcher function with error recovery.
    
    Args:
        func: Original watcher function
    
    Returns:
        Wrapped function with error handling
    """
    @safe_watcher_operation
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def wrap_file_detection(func: Callable) -> Callable:
    """Wrap file detection function."""
    @safe_watcher_operation
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# Task Processor Wrappers
# ============================================================

def wrap_task_processor(func: Callable) -> Callable:
    """
    Wrap a task processor function with error recovery.
    
    Args:
        func: Original task processor function
    
    Returns:
        Wrapped function with error handling
    """
    @safe_task_processing
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def wrap_task_action(func: Callable, action_type: str = "task_action") -> Callable:
    """
    Wrap a specific task action with error recovery.
    
    Args:
        func: Function to wrap
        action_type: Type of action for logging
    
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="task_action")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type=action_type, max_retries=2)
    return wrapper


# ============================================================
# MCP Server Wrappers
# ============================================================

def wrap_mcp_call(func: Callable) -> Callable:
    """
    Wrap an MCP server call with error recovery.
    
    Args:
        func: Original MCP call function
    
    Returns:
        Wrapped function with error handling
    """
    @safe_mcp_call
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def wrap_mcp_email_action(func: Callable) -> Callable:
    """Wrap MCP email action (no auto-retry for external emails)."""
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="mcp_email")
        
        def execute():
            return func(*args, **kwargs)
        
        # Email actions are not safe to retry automatically
        return recovery.execute(execute, action_type="external_email", max_retries=0)
    return wrapper


def wrap_mcp_post_action(func: Callable) -> Callable:
    """Wrap MCP social media post action (no auto-retry)."""
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="mcp_post")
        
        def execute():
            return func(*args, **kwargs)
        
        # Post actions are not safe to retry automatically
        return recovery.execute(execute, action_type="social_media_post", max_retries=0)
    return wrapper


# ============================================================
# Accounting Wrappers
# ============================================================

def wrap_accounting_update(func: Callable) -> Callable:
    """
    Wrap an accounting update function with error recovery.
    
    Args:
        func: Original accounting function
    
    Returns:
        Wrapped function with error handling
    """
    @safe_accounting_update
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def wrap_ledger_entry(func: Callable) -> Callable:
    """Wrap ledger entry creation."""
    @safe_accounting_update
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def wrap_summary_generation(func: Callable) -> Callable:
    """Wrap summary/report generation."""
    @safe_report_generation
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# Scheduler Wrappers
# ============================================================

def wrap_scheduler_cycle(func: Callable) -> Callable:
    """
    Wrap a scheduler cycle function with error recovery.
    Ensures one component failure doesn't stop the entire cycle.
    
    Args:
        func: Scheduler cycle function
    
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="scheduler")
        health = get_system_health()
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log error but don't crash the scheduler
            recovery.log_error(e, "scheduler_cycle", 0, 0)
            health.mark_unhealthy("scheduler", e)
            
            # Return safe response
            return handle_error_gracefully(
                e, "scheduler", "cycle_execution",
                default_return={"status": "error", "recovered": True}
            )
    return wrapper


def wrap_component_execution(func: Callable, component_name: str) -> Callable:
    """
    Wrap a component execution with isolated error handling.
    
    Args:
        func: Component function
        component_name: Name of the component
    
    Returns:
        Wrapped function that won't crash the scheduler
    """
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name=component_name)
        health = get_system_health()
        
        try:
            result = func(*args, **kwargs)
            
            # Mark healthy on success
            if health.is_healthy(component_name) is False:
                health.mark_healthy(component_name)
            
            return result
            
        except Exception as e:
            recovery.log_error(e, component_name, 0, 0)
            health.mark_unhealthy(component_name, e)
            
            # Return safe error response
            return {
                "status": "error",
                "component": component_name,
                "error": str(e),
                "recovered": True
            }
    return wrapper


# ============================================================
# Generic Safe Execution
# ============================================================

def safe_execute(func: Callable, component: str, action: str,
                 default_return: Any = None, max_retries: int = 2) -> Any:
    """
    Safely execute any function with error recovery.
    
    This is a generic wrapper that can be used for any operation.
    
    Args:
        func: Function to execute
        component: Component name for logging
        action: Action description for logging
        default_return: Default value to return on error
        max_retries: Maximum retry attempts
    
    Returns:
        Function result or default/error response
    """
    recovery = ErrorRecovery(component_name=component)
    
    def execute():
        return func()
    
    result = recovery.execute(execute, action_type=action, max_retries=max_retries)
    
    # If we got an error response and have a default, use default
    if isinstance(result, dict) and not result.get("success", True):
        if default_return is not None:
            return default_return
    
    return result


def safe_execute_with_fallback(func: Callable, fallback: Callable,
                               component: str, action: str) -> Any:
    """
    Execute function with fallback on error.
    
    Args:
        func: Primary function to execute
        fallback: Fallback function if primary fails
        component: Component name
        action: Action description
    
    Returns:
        Primary result or fallback result
    """
    recovery = ErrorRecovery(component_name=component)
    
    try:
        return func()
    except Exception as e:
        recovery.log_error(e, action, 0, 0)
        logger.warning(f"Primary action '{action}' failed, using fallback")
        
        try:
            return fallback()
        except Exception as fallback_error:
            recovery.log_error(fallback_error, f"{action}_fallback", 0, 0)
            return handle_error_gracefully(
                fallback_error, component, action,
                default_return={"status": "error", "recovered": True}
            )


# ============================================================
# Integration Helper Functions
# ============================================================

def create_safe_wrapper_for_module(module, component_name: str) -> Dict[str, Callable]:
    """
    Create safe wrappers for all public functions in a module.
    
    Args:
        module: Module to wrap
        component_name: Component name for logging
    
    Returns:
        Dictionary of wrapped functions
    """
    wrapped = {}
    
    for name in dir(module):
        if not name.startswith('_'):
            attr = getattr(module, name)
            if callable(attr) and hasattr(attr, '__module__'):
                if attr.__module__ == module.__name__:
                    wrapped[name] = wrap_component_execution(attr, component_name)
    
    return wrapped


def log_component_start(component: str, action: str) -> None:
    """Log component action start."""
    timestamp = datetime.now().isoformat()
    logger.info(f"[{timestamp}] COMPONENT_START | {component} | {action}")


def log_component_end(component: str, action: str, success: bool) -> None:
    """Log component action end."""
    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "ERROR"
    logger.info(f"[{timestamp}] COMPONENT_END | {component} | {action} | {status}")


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    print("Error Recovery Wrappers - Example Usage")
    print("=" * 50)
    
    # Example: Wrap a function
    def example_task():
        print("Executing task...")
        return "Task completed"
    
    safe_task = wrap_task_processor(example_task)
    result = safe_task()
    print(f"Result: {result}")
    
    # Example: Safe execute
    def risky_operation():
        raise ValueError("Something went wrong!")
    
    result = safe_execute(
        risky_operation,
        component="test",
        action="risky_operation",
        default_return={"status": "fallback"}
    )
    print(f"Safe execute result: {result}")
    
    print("\n" + "=" * 50)
    print("Examples complete!")
