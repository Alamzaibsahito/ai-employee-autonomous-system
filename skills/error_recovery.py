"""
Error Recovery Module

A centralized error handling and recovery system for the Personal AI Employee.
Provides error categorization, retry logic, graceful degradation, and logging.

This module wraps all critical operations to ensure:
- Failures are caught and categorized
- Safe retries with exponential backoff
- System continues operating even if components fail
- All errors are logged for debugging
- Unrecoverable errors are escalated

Usage:
    from skills.error_recovery import with_error_recovery, ErrorRecovery
    
    # Wrap a function with error recovery
    @with_error_recovery(max_retries=3)
    def my_function():
        ...
    
    # Or use the class directly
    recovery = ErrorRecovery()
    result = recovery.execute(my_function, action_type="task_processing")
"""

import os
import time
import random
import logging
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Error log file path
ERROR_LOG_PATH = "Logs/error_recovery.log"

# Ensure Logs directory exists
os.makedirs("Logs", exist_ok=True)


# ============================================================
# Error Categories
# ============================================================

class ErrorCategory(Enum):
    """Error categories for classification and handling."""
    TRANSIENT = "transient"           # Temporary, retry OK
    AUTHENTICATION = "authentication"  # Auth/permission, escalate
    LOGIC = "logic"                    # Business rule violation, escalate
    DATA = "data"                      # Corrupt/malformed data, escalate
    SYSTEM = "system"                  # Infrastructure failure, alert


class ErrorRecoveryError(Exception):
    """Base exception for error recovery system."""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.LOGIC):
        super().__init__(message)
        self.category = category
        self.timestamp = datetime.now()


class TransientError(ErrorRecoveryError):
    """Temporary error that may resolve on retry."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.TRANSIENT)


class AuthenticationError(ErrorRecoveryError):
    """Authentication or permission error."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.AUTHENTICATION)


class LogicError(ErrorRecoveryError):
    """Business logic or workflow violation."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.LOGIC)


class DataError(ErrorRecoveryError):
    """Data corruption or format error."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.DATA)


class SystemError(ErrorRecoveryError):
    """System or infrastructure failure."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.SYSTEM)


# ============================================================
# Retry Configuration
# ============================================================

RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay_seconds": 1,
    "max_delay_seconds": 30,
    "exponential_base": 2,
    "jitter": True,
}

# Actions that should NEVER be automatically retried
NO_RETRY_ACTIONS = [
    "payment",
    "financial_transaction",
    "external_email",
    "social_media_post",
    "file_delete",
    "database_write",
    "external_api_mutation",
    "send_email",
    "create_post",
    "schedule_post",
]


# ============================================================
# Error Recovery Class
# ============================================================

class ErrorRecovery:
    """
    Centralized error recovery handler.
    
    Provides:
    - Error categorization
    - Retry with exponential backoff
    - Graceful degradation
    - Comprehensive logging
    """
    
    def __init__(self, component_name: str = "unknown"):
        self.component_name = component_name
        self.retry_count = 0
        self.error_history: List[Dict] = []
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize an error for appropriate handling.
        
        Args:
            error: The exception to categorize
        
        Returns:
            ErrorCategory enum value
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Check for known error types
        if isinstance(error, ErrorRecoveryError):
            return error.category
        
        # Transient errors (temporary, retry OK)
        transient_indicators = [
            "timeout", "timed out", "connection", "network",
            "locked", "busy", "rate limit", "too many requests",
            "temporarily unavailable", "retry", "connection refused",
            "connection reset", "connection aborted"
        ]
        if any(indicator in error_msg for indicator in transient_indicators):
            return ErrorCategory.TRANSIENT
        
        # Authentication errors (escalate immediately)
        auth_indicators = [
            "auth", "permission", "denied", "unauthorized",
            "forbidden", "invalid token", "expired", "credential",
            "access denied", "authentication failed"
        ]
        if any(indicator in error_msg for indicator in auth_indicators):
            return ErrorCategory.AUTHENTICATION
        
        # Data errors (escalate)
        data_indicators = [
            "parse", "invalid format", "corrupt", "encoding",
            "yaml", "json", "malformed", "schema", "type error"
        ]
        if any(indicator in error_msg for indicator in data_indicators):
            return ErrorCategory.DATA
        
        # Logic errors (escalate)
        logic_indicators = [
            "missing", "required", "invalid state", "workflow",
            "not found", "does not exist", "key error"
        ]
        if any(indicator in error_msg for indicator in logic_indicators):
            return ErrorCategory.LOGIC
        
        # System errors (alert and degrade)
        system_indicators = [
            "disk", "memory", "permission denied", "os error",
            "i/o error", "no space", "resource"
        ]
        if any(indicator in error_msg for indicator in system_indicators):
            return ErrorCategory.SYSTEM
        
        # Default to transient for unknown errors (safe to retry once)
        return ErrorCategory.TRANSIENT
    
    def calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        base = RETRY_CONFIG["base_delay_seconds"]
        exp_base = RETRY_CONFIG["exponential_base"]
        max_delay = RETRY_CONFIG["max_delay_seconds"]
        
        # Exponential backoff: base * (2 ^ attempt)
        delay = base * (exp_base ** attempt)
        
        # Add jitter to prevent thundering herd
        if RETRY_CONFIG["jitter"]:
            jitter = random.uniform(0, 0.5)
            delay += jitter
        
        # Cap at maximum delay
        return min(delay, max_delay)
    
    def is_safe_to_retry(self, action_type: str) -> bool:
        """
        Check if an action type is safe for automatic retry.
        
        Args:
            action_type: Type of action being performed
        
        Returns:
            True if safe to retry, False otherwise
        """
        action_lower = action_type.lower()
        
        # Check against NO_RETRY list
        for no_retry in NO_RETRY_ACTIONS:
            if no_retry in action_lower:
                return False
        
        return True
    
    def log_error(self, error: Exception, action: str, attempt: int = 0,
                  retry_delay: float = 0, context: Optional[Dict] = None) -> None:
        """
        Log an error to the error recovery log file.
        
        Args:
            error: The exception that occurred
            action: Name/description of the failed action
            attempt: Current attempt number
            retry_delay: Delay before next retry (if applicable)
            context: Optional additional context
        """
        timestamp = datetime.now().isoformat()
        category = self.categorize_error(error)
        
        # Build log entry
        log_entry = {
            "timestamp": timestamp,
            "component": self.component_name,
            "action": action,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "category": category.value,
            "attempt": attempt + 1,
            "retry_delay": retry_delay,
            "context": context or {}
        }
        
        # Store in history
        self.error_history.append(log_entry)
        
        # Format log line
        log_line = (
            f"[{timestamp}] ERROR | Component: {self.component_name} | "
            f"Action: {action} | Category: {category.value} | "
            f"Attempt: {attempt + 1} | Error: {type(error).__name__}: {error}"
        )
        
        if retry_delay > 0:
            log_line += f" | Retrying in {retry_delay:.1f}s"
        
        # Write to log file
        try:
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write to error log: {e}")
        
        # Also log via standard logging
        logger.error(log_line)
    
    def log_retry_exhausted(self, action: str, total_attempts: int) -> None:
        """Log when all retries are exhausted."""
        timestamp = datetime.now().isoformat()
        log_line = (
            f"[{timestamp}] MAX_RETRIES | Component: {self.component_name} | "
            f"Action: {action} | Total attempts: {total_attempts} | "
            f"Status: NEEDS_HUMAN_REVIEW"
        )
        
        try:
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write to error log: {e}")
        
        logger.warning(log_line)
    
    def log_recovery_success(self, action: str, attempts: int) -> None:
        """Log successful recovery after retry."""
        timestamp = datetime.now().isoformat()
        log_line = (
            f"[{timestamp}] RECOVERY | Component: {self.component_name} | "
            f"Action: {action} | Succeeded after {attempts} attempt(s)"
        )
        
        try:
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write to error log: {e}")
        
        logger.info(log_line)
    
    def execute(self, func: Callable, action_type: str = "generic",
                max_retries: Optional[int] = None,
                context: Optional[Dict] = None) -> Any:
        """
        Execute a function with error recovery.
        
        Args:
            func: Function to execute
            action_type: Type of action (for retry safety check)
            max_retries: Override default max retries
            context: Optional context for logging
        
        Returns:
            Result of the function
        
        Raises:
            Exception: If all retries exhausted or error is not retryable
        """
        max_retries = max_retries if max_retries is not None else RETRY_CONFIG["max_retries"]
        context = context or {}
        
        # Check if action is safe to retry
        safe_to_retry = self.is_safe_to_retry(action_type)
        
        last_exception = None
        attempt = 0
        
        while attempt <= max_retries:
            try:
                # Execute the function
                result = func()
                
                # Log success if there were previous failures
                if attempt > 0:
                    self.log_recovery_success(action_type, attempt + 1)
                
                return result
                
            except Exception as e:
                last_exception = e
                category = self.categorize_error(e)
                
                # Log the error
                if attempt < max_retries and safe_to_retry and category == ErrorCategory.TRANSIENT:
                    delay = self.calculate_backoff_delay(attempt)
                    self.log_error(e, action_type, attempt, delay, context)
                    
                    # Wait before retry
                    time.sleep(delay)
                    attempt += 1
                else:
                    # Don't retry - log and either raise or handle gracefully
                    self.log_error(e, action_type, attempt, 0, context)
                    
                    # Log max retries if applicable
                    if attempt >= max_retries:
                        self.log_retry_exhausted(action_type, attempt + 1)
                    
                    # For non-transient errors or unsafe actions, raise immediately
                    if not safe_to_retry:
                        logger.warning(f"Action '{action_type}' is not safe to retry. Escalating.")
                    elif category != ErrorCategory.TRANSIENT:
                        logger.warning(f"Error category '{category.value}' is not retryable. Escalating.")
                    
                    # Return safe error response instead of crashing
                    return self._create_safe_error_response(e, action_type, context)
        
        # Should not reach here, but handle gracefully
        return self._create_safe_error_response(last_exception, action_type, context)
    
    def _create_safe_error_response(self, error: Exception, action_type: str,
                                    context: Dict) -> Dict:
        """Create a safe structured error response."""
        return {
            "success": False,
            "error": str(error),
            "error_type": type(error).__name__,
            "category": self.categorize_error(error).value,
            "action": action_type,
            "component": self.component_name,
            "timestamp": datetime.now().isoformat(),
            "needs_human_review": True,
            "context": context
        }


# ============================================================
# Decorator for Easy Wrapping
# ============================================================

def with_error_recovery(component: str = "unknown",
                        action_type: str = "generic",
                        max_retries: int = 3,
                        return_on_error: Optional[Any] = None):
    """
    Decorator to wrap a function with error recovery.
    
    Args:
        component: Name of the component calling this function
        action_type: Type of action for retry safety check
        max_retries: Maximum retry attempts
        return_on_error: Value to return on error (default: error dict)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            recovery = ErrorRecovery(component_name=component)
            
            def execute_func():
                return func(*args, **kwargs)
            
            result = recovery.execute(
                execute_func,
                action_type=action_type,
                max_retries=max_retries
            )
            
            # If we got an error response and have a custom return value
            if isinstance(result, dict) and not result.get("success", True):
                if return_on_error is not None:
                    return return_on_error
            
            return result
        
        return wrapper
    return decorator


# ============================================================
# Component-Specific Wrappers
# ============================================================

def safe_watcher_operation(func: Callable) -> Callable:
    """Wrapper for vault watcher operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="vault_watcher")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type="file_watching", max_retries=2)
    return wrapper


def safe_task_processing(func: Callable) -> Callable:
    """Wrapper for task processing operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="task_processor")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type="task_processing", max_retries=2)
    return wrapper


def safe_mcp_call(func: Callable) -> Callable:
    """Wrapper for MCP server calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="mcp_client")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type="mcp_call", max_retries=3)
    return wrapper


def safe_accounting_update(func: Callable) -> Callable:
    """Wrapper for accounting updates."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="accounting")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type="accounting_update", max_retries=2)
    return wrapper


def safe_report_generation(func: Callable) -> Callable:
    """Wrapper for report generation."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        recovery = ErrorRecovery(component_name="report_generator")
        
        def execute():
            return func(*args, **kwargs)
        
        return recovery.execute(execute, action_type="report_generation", max_retries=2)
    return wrapper


# ============================================================
# Graceful Degradation
# ============================================================

class SystemHealth:
    """
    Track system health and apply graceful degradation.
    """
    
    def __init__(self):
        self.component_status: Dict[str, str] = {
            "vault_watcher": "healthy",
            "task_processor": "healthy",
            "approval_checker": "healthy",
            "accounting": "healthy",
            "mcp_servers": "healthy",
            "scheduler": "healthy"
        }
        self.error_counts: Dict[str, int] = {}
    
    def mark_unhealthy(self, component: str, error: Exception) -> None:
        """Mark a component as unhealthy."""
        self.component_status[component] = "unhealthy"
        self.error_counts[component] = self.error_counts.get(component, 0) + 1
        
        logger.warning(f"Component '{component}' marked unhealthy: {error}")
    
    def mark_healthy(self, component: str) -> None:
        """Mark a component as healthy."""
        self.component_status[component] = "healthy"
        logger.info(f"Component '{component}' marked healthy")
    
    def is_healthy(self, component: str) -> bool:
        """Check if a component is healthy."""
        return self.component_status.get(component, "unknown") == "healthy"
    
    def get_degradation_level(self) -> int:
        """
        Get current system degradation level.
        
        Returns:
            0: Full operation
            1: Degraded (1-2 components unhealthy)
            2: Limited (3-4 components unhealthy)
            3: Safe mode (5+ components unhealthy)
        """
        unhealthy_count = sum(
            1 for status in self.component_status.values()
            if status == "unhealthy"
        )
        
        if unhealthy_count == 0:
            return 0
        elif unhealthy_count <= 2:
            return 1
        elif unhealthy_count <= 4:
            return 2
        else:
            return 3
    
    def get_status_report(self) -> Dict:
        """Get current system status report."""
        return {
            "component_status": self.component_status,
            "degradation_level": self.get_degradation_level(),
            "error_counts": self.error_counts,
            "timestamp": datetime.now().isoformat()
        }


# Global system health tracker
system_health = SystemHealth()


def get_system_health() -> SystemHealth:
    """Get the global system health tracker."""
    return system_health


# ============================================================
# Utility Functions
# ============================================================

def handle_error_gracefully(error: Exception, component: str,
                            action: str, default_return: Any = None) -> Any:
    """
    Handle an error gracefully and return a safe default.
    
    Args:
        error: The exception that occurred
        component: Component name
        action: Action that failed
        default_return: Default value to return
    
    Returns:
        Default return value or error dict
    """
    recovery = ErrorRecovery(component_name=component)
    recovery.log_error(error, action, 0, 0)
    
    if default_return is not None:
        return default_return
    
    return {
        "success": False,
        "error": str(error),
        "component": component,
        "action": action,
        "timestamp": datetime.now().isoformat()
    }


def retry_on_transient_error(func: Callable, max_retries: int = 3,
                             base_delay: float = 1.0) -> Any:
    """
    Execute a function with retry on transient errors only.
    
    Args:
        func: Function to execute
        max_retries: Maximum retry attempts
        base_delay: Base delay between retries
    
    Returns:
        Function result or error dict
    """
    recovery = ErrorRecovery(component_name="retry_helper")
    
    def execute():
        return func()
    
    return recovery.execute(execute, action_type="transient_retry", max_retries=max_retries)


# ============================================================
# CLI Entry Point for Testing
# ============================================================

if __name__ == "__main__":
    print("Error Recovery Module - Test Suite")
    print("=" * 50)
    
    # Test 1: Successful execution
    print("\n1. Testing successful execution...")
    recovery = ErrorRecovery(component_name="test")
    
    def success_func():
        return "Success!"
    
    result = recovery.execute(success_func, action_type="test_success")
    print(f"   Result: {result}")
    
    # Test 2: Transient error with retry
    print("\n2. Testing transient error with retry...")
    attempt_count = [0]
    
    def transient_func():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise TimeoutError("Connection timeout")
        return "Recovered!"
    
    result = recovery.execute(transient_func, action_type="test_transient", max_retries=3)
    print(f"   Result: {result}")
    print(f"   Attempts: {attempt_count[0]}")
    
    # Test 3: Non-retryable action
    print("\n3. Testing non-retryable action (payment)...")
    
    def payment_func():
        raise ConnectionError("Payment gateway error")
    
    result = recovery.execute(payment_func, action_type="payment", max_retries=3)
    print(f"   Result: {result}")
    print(f"   Needs human review: {result.get('needs_human_review', False)}")
    
    # Test 4: Decorator usage
    print("\n4. Testing decorator...")
    
    @with_error_recovery(component="test_decorator", action_type="test", max_retries=2)
    def decorated_func():
        return "Decorated success!"
    
    result = decorated_func()
    print(f"   Result: {result}")
    
    # Test 5: System health
    print("\n5. Testing system health tracking...")
    health = get_system_health()
    health.mark_unhealthy("test_component", Exception("Test error"))
    print(f"   Degradation level: {health.get_degradation_level()}")
    print(f"   Status report: {health.get_status_report()}")
    
    print("\n" + "=" * 50)
    print("Test suite complete!")
    print(f"Error log written to: {ERROR_LOG_PATH}")
