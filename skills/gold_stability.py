"""
Gold Tier Stability Module

Provides:
1. Graceful Degradation - System continues even if components fail
2. Cross-Domain Integration - Business tasks auto-trigger accounting
3. Safety Checks - Prevent infinite loops and cascading failures

This module wraps all critical operations to ensure hackathon-ready stability.
"""

import os
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# Import error recovery
try:
    from .error_recovery import (
        ErrorRecovery,
        get_system_health,
        handle_error_gracefully,
    )
except ImportError:
    from error_recovery import (
        ErrorRecovery,
        get_system_health,
        handle_error_gracefully,
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure Logs directory exists
os.makedirs("Logs", exist_ok=True)

# Stability log file
STABILITY_LOG_PATH = "Logs/stability.log"

# Business keywords for cross-domain detection
BUSINESS_KEYWORDS = {
    'income': [
        'client', 'payment', 'revenue', 'sale', 'invoice', 'received',
        'customer', 'contract', 'deal', 'income', 'earnings', 'profit'
    ],
    'expense': [
        'expense', 'cost', 'purchase', 'vendor', 'supplier', 'bill',
        'subscription', 'rent', 'utilities', 'equipment', 'supplies',
        'contractor', 'freelancer', 'salary', 'wages', 'tax', 'fee'
    ],
    'invoice': [
        'invoice', 'billing', 'quote', 'estimate', 'proposal',
        'payment request', 'payment due', 'accounts receivable'
    ]
}


# ============================================================
# Graceful Degradation Wrapper
# ============================================================

class GracefulDegradation:
    """
    Ensures system continues operating even if components fail.
    
    Features:
    - Safe MCP call execution
    - Partial failure handling
    - Component isolation
    - Automatic fallback
    """
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.recovery = ErrorRecovery(component_name=component_name)
        self.health = get_system_health()
    
    def safe_mcp_call(self, mcp_func: Callable, action_type: str,
                      default_return: Any = None) -> Any:
        """
        Execute MCP call with graceful degradation.
        
        Args:
            mcp_func: MCP server function to call
            action_type: Type of action (email, post, etc.)
            default_return: Fallback value if MCP fails
        
        Returns:
            MCP result or safe fallback
        """
        try:
            # Execute with timeout and error handling
            result = self.recovery.execute(
                mcp_func,
                action_type=action_type,
                max_retries=1  # Only one retry for MCP calls
            )
            
            # Check if result indicates failure
            if isinstance(result, dict) and not result.get('success', True):
                logger.warning(f"MCP call '{action_type}' failed gracefully")
                self.health.mark_unhealthy("mcp_servers", Exception(result.get('error', 'Unknown error')))
                
                if default_return is not None:
                    return default_return
                
                return {
                    'success': False,
                    'partial_failure': True,
                    'action': action_type,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Success - mark healthy
            self.health.mark_healthy("mcp_servers")
            return result
            
        except Exception as e:
            logger.error(f"MCP call failed: {e}")
            self.health.mark_unhealthy("mcp_servers", e)
            
            # Return safe fallback
            if default_return is not None:
                return default_return
            
            return handle_error_gracefully(
                e, self.component_name, action_type,
                default_return={'success': False, 'partial_failure': True}
            )
    
    def safe_skill_execution(self, skill_func: Callable, skill_name: str,
                             default_return: Any = None) -> Any:
        """
        Execute skill with graceful degradation.
        
        Args:
            skill_func: Skill function to execute
            skill_name: Name of the skill
            default_return: Fallback value if skill fails
        
        Returns:
            Skill result or safe fallback
        """
        try:
            result = skill_func()
            
            # Mark healthy on success
            self.health.mark_healthy(skill_name)
            return result
            
        except Exception as e:
            logger.error(f"Skill '{skill_name}' failed: {e}")
            self.health.mark_unhealthy(skill_name, e)
            
            # Log to stability log
            self._log_stability_event(skill_name, str(e))
            
            # Return safe fallback
            if default_return is not None:
                return default_return
            
            return handle_error_gracefully(
                e, self.component_name, skill_name,
                default_return={'success': False, 'skill_failed': skill_name}
            )
    
    def _log_stability_event(self, component: str, error: str) -> None:
        """Log stability event to stability log."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] DEGRADATION | {self.component_name} | {component} | {error}\n"
        
        try:
            with open(STABILITY_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write stability log: {e}")


# ============================================================
# Cross-Domain Integration
# ============================================================

class CrossDomainIntegration:
    """
    Integrates business tasks with accounting automatically.
    
    Features:
    - Business keyword detection
    - Automatic accounting triggers
    - CEO briefing updates
    """
    
    def __init__(self):
        self.recovery = ErrorRecovery(component_name="cross_domain")
        self.accounting_module = None
        self._load_accounting_module()
    
    def _load_accounting_module(self) -> None:
        """Load accounting module if available."""
        try:
            import accounting_skill
            self.accounting_module = accounting_skill
            logger.info("Accounting module loaded for cross-domain integration")
        except ImportError:
            logger.warning("Accounting module not available - cross-domain disabled")
            self.accounting_module = None
    
    def detect_business_intent(self, text: str) -> Optional[str]:
        """
        Detect business intent from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            'income', 'expense', 'invoice', or None
        """
        text_lower = text.lower()
        
        # Check for invoice first (higher priority)
        for keyword in BUSINESS_KEYWORDS['invoice']:
            if keyword in text_lower:
                return 'invoice'
        
        # Check for income
        for keyword in BUSINESS_KEYWORDS['income']:
            if keyword in text_lower:
                return 'income'
        
        # Check for expenses
        for keyword in BUSINESS_KEYWORDS['expense']:
            if keyword in text_lower:
                return 'expense'
        
        return None
    
    def extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text."""
        import re
        
        patterns = [
            r'\$(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)',
            r'\$(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:dollars?|USD|usd)',
            r'amount[:\s]+\$?(\d+\.?\d*)',
            r'payment[:\s]+\$?(\d+\.?\d*)',
            r'cost[:\s]+\$?(\d+\.?\d*)',
            r'price[:\s]+\$?(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def auto_trigger_accounting(self, task_content: str, task_file: str) -> Optional[Dict[str, Any]]:
        """
        Automatically trigger accounting for business tasks.
        
        Args:
            task_content: Full task content
            task_file: Task filename
        
        Returns:
            Accounting result or None if not business-related
        """
        # Detect business intent
        intent = self.detect_business_intent(task_content)
        
        if not intent:
            return None
        
        # Extract amount
        amount = self.extract_amount(task_content) or 0.0
        
        # Extract description
        description = task_content[:200] if len(task_content) > 200 else task_content
        
        # Trigger accounting
        if self.accounting_module:
            try:
                if intent == 'income':
                    result = self.accounting_module.record_income(
                        description=description,
                        amount=amount,
                        source=f"Task:{task_file}"
                    )
                elif intent == 'expense':
                    result = self.accounting_module.record_expense(
                        description=description,
                        amount=amount,
                        source=f"Task:{task_file}"
                    )
                elif intent == 'invoice':
                    result = self.accounting_module.record_invoice(
                        description=description,
                        amount=amount,
                        source=f"Task:{task_file}"
                    )
                else:
                    result = None
                
                if result:
                    logger.info(f"Cross-domain: Auto-recorded {intent} for task {task_file}")
                    
                    # Update weekly summary
                    self._update_ceo_briefing()
                    
                    return result
                    
            except Exception as e:
                logger.error(f"Failed to trigger accounting: {e}")
                self.recovery.log_error(e, "accounting_trigger", 0, 0, {'task': task_file})
        
        return None
    
    def _update_ceo_briefing(self) -> None:
        """Update CEO weekly briefing with latest data."""
        if self.accounting_module:
            try:
                self.accounting_module.generate_weekly_summary(force_update=True)
                logger.info("CEO briefing updated with latest data")
            except Exception as e:
                logger.error(f"Failed to update CEO briefing: {e}")


# ============================================================
# Safety Checks
# ============================================================

class SafetyChecks:
    """
    Prevents infinite loops and ensures system stability.
    
    Features:
    - Max iteration limits
    - Loop detection
    - Resource monitoring
    - Cascade failure prevention
    """
    
    def __init__(self):
        self.iteration_counters: Dict[str, int] = {}
        self.max_iterations = 10  # Per task
        self.max_total_iterations = 100  # Per cycle
    
    def check_iteration_limit(self, task_id: str) -> bool:
        """
        Check if task has exceeded iteration limit.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if within limit, False if exceeded
        """
        current = self.iteration_counters.get(task_id, 0)
        
        if current >= self.max_iterations:
            logger.warning(f"Task {task_id} exceeded max iterations ({self.max_iterations})")
            return False
        
        self.iteration_counters[task_id] = current + 1
        return True
    
    def check_total_iterations(self, cycle_count: int) -> bool:
        """
        Check if total cycle iterations exceeded.
        
        Args:
            cycle_count: Current cycle count
        
        Returns:
            True if within limit, False if exceeded
        """
        if cycle_count >= self.max_total_iterations:
            logger.warning(f"Total iterations exceeded limit ({self.max_total_iterations})")
            return False
        
        return True
    
    def reset_task_counter(self, task_id: str) -> None:
        """Reset iteration counter for a task."""
        self.iteration_counters[task_id] = 0
    
    def reset_all_counters(self) -> None:
        """Reset all iteration counters."""
        self.iteration_counters.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """Get safety status."""
        return {
            'active_tasks': len(self.iteration_counters),
            'max_per_task': self.max_iterations,
            'max_total': self.max_total_iterations,
            'counters': dict(self.iteration_counters)
        }


# ============================================================
# Scheduler Stability Wrapper
# ============================================================

class SchedulerStability:
    """
    Ensures scheduler continues even if individual skills fail.
    
    Features:
    - Component isolation
    - Failure containment
    - Continued execution
    """
    
    def __init__(self):
        self.recovery = ErrorRecovery(component_name="scheduler")
        self.health = get_system_health()
        self.degradation = GracefulDegradation("scheduler")
    
    def safe_component_execution(self, component_func: Callable,
                                 component_name: str) -> Dict[str, Any]:
        """
        Execute scheduler component with full isolation.
        
        Args:
            component_func: Component function to execute
            component_name: Component name
        
        Returns:
            Component result or error dict
        """
        try:
            result = component_func()
            
            # Success - mark healthy
            self.health.mark_healthy(component_name)
            return result
            
        except Exception as e:
            # Log error
            self.recovery.log_error(e, component_name, 0, 0)
            
            # Mark unhealthy
            self.health.mark_unhealthy(component_name, e)
            
            # Log to stability log
            logger.error(f"Component {component_name} failed - continuing with other components")
            
            # Return safe error response
            return {
                'status': 'error',
                'component': component_name,
                'error': str(e),
                'recovered': True,
                'timestamp': datetime.now().isoformat()
            }
    
    def run_scheduler_cycle(self, components: List[Dict]) -> Dict[str, Any]:
        """
        Run full scheduler cycle with component isolation.
        
        Args:
            components: List of component dicts with 'name' and 'func'
        
        Returns:
            Cycle results
        """
        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'components_run': 0,
            'components_failed': 0,
            'results': []
        }
        
        for component in components:
            name = component.get('name', 'unknown')
            func = component.get('func')
            
            if not func:
                continue
            
            # Execute with isolation
            result = self.safe_component_execution(func, name)
            
            cycle_results['results'].append({
                'component': name,
                'result': result
            })
            
            if isinstance(result, dict) and result.get('status') == 'error':
                cycle_results['components_failed'] += 1
            else:
                cycle_results['components_run'] += 1
        
        # Log cycle summary
        logger.info(
            f"Scheduler cycle complete: "
            f"{cycle_results['components_run']} succeeded, "
            f"{cycle_results['components_failed']} failed"
        )
        
        return cycle_results


# ============================================================
# Gold Tier Stability Controller
# ============================================================

class GoldTierStability:
    """
    Main controller for Gold Tier stability features.
    
    Combines:
    - Graceful degradation
    - Cross-domain integration
    - Safety checks
    - Scheduler stability
    """
    
    def __init__(self):
        self.degradation = GracefulDegradation("gold_tier")
        self.cross_domain = CrossDomainIntegration()
        self.safety = SafetyChecks()
        self.scheduler = SchedulerStability()
        self.health = get_system_health()
    
    def safe_execute_task(self, task_func: Callable, task_id: str,
                          task_content: str) -> Any:
        """
        Execute task with full Gold Tier stability.
        
        Args:
            task_func: Task execution function
            task_id: Task identifier
            task_content: Task content for cross-domain detection
        
        Returns:
            Task result
        """
        # Check iteration limit
        if not self.safety.check_iteration_limit(task_id):
            logger.error(f"Task {task_id} exceeded iteration limit")
            return {
                'success': False,
                'error': 'Max iterations exceeded',
                'needs_human_review': True
            }
        
        # Cross-domain: Auto-trigger accounting for business tasks
        self.cross_domain.auto_trigger_accounting(task_content, task_id)
        
        # Execute task with graceful degradation
        return self.degradation.safe_skill_execution(
            task_func,
            f"task_{task_id}",
            default_return={'success': False, 'partial_failure': True}
        )
    
    def safe_mcp_action(self, mcp_func: Callable, action_type: str) -> Any:
        """
        Execute MCP action with graceful degradation.
        
        Args:
            mcp_func: MCP function to call
            action_type: Type of action
        
        Returns:
            MCP result or safe fallback
        """
        return self.degradation.safe_mcp_call(
            mcp_func,
            action_type,
            default_return={'success': False, 'partial_failure': True}
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            'health': self.health.get_status_report(),
            'safety': self.safety.get_status(),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# Convenience Functions
# ============================================================

# Global stability controller
_stability_controller = None

def get_stability_controller() -> GoldTierStability:
    """Get or create global stability controller."""
    global _stability_controller
    if _stability_controller is None:
        _stability_controller = GoldTierStability()
    return _stability_controller


def safe_mcp_call(mcp_func: Callable, action_type: str) -> Any:
    """Convenience function for safe MCP calls."""
    controller = get_stability_controller()
    return controller.safe_mcp_action(mcp_func, action_type)


def detect_business_intent(text: str) -> Optional[str]:
    """Convenience function for business intent detection."""
    controller = get_stability_controller()
    return controller.cross_domain.detect_business_intent(text)


def auto_trigger_accounting(task_content: str, task_file: str) -> Optional[Dict]:
    """Convenience function for auto-triggering accounting."""
    controller = get_stability_controller()
    return controller.cross_domain.auto_trigger_accounting(task_content, task_file)


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Gold Tier Stability Module - Test Suite")
    print("=" * 60)
    
    # Test 1: Business intent detection
    print("\n1. Testing business intent detection...")
    test_texts = [
        ("Client payment received $5000", "income"),
        ("Office supplies expense $150", "expense"),
        ("Invoice generated for services", "invoice"),
        ("Regular task with no business", None)
    ]
    
    controller = get_stability_controller()
    
    for text, expected in test_texts:
        result = controller.cross_domain.detect_business_intent(text)
        status = "OK" if result == expected else "FAIL"
        print(f"   [{status}] '{text[:40]}...' -> {result}")
    
    # Test 2: Amount extraction
    print("\n2. Testing amount extraction...")
    amount_tests = [
        ("Payment of $5000 received", 5000.0),
        ("Cost: $150.50", 150.50),
        ("No amount here", None)
    ]
    
    for text, expected in amount_tests:
        result = controller.cross_domain.extract_amount(text)
        status = "OK" if result == expected else "FAIL"
        print(f"   [{status}] '{text}' -> ${result}")
    
    # Test 3: Safety checks
    print("\n3. Testing safety checks...")
    safety = controller.safety
    
    # Test iteration limit
    for i in range(12):
        allowed = safety.check_iteration_limit("test_task")
        if i < 10:
            status = "OK" if allowed else "FAIL"
            print(f"   [{status}] Iteration {i+1}: {'Allowed' if allowed else 'Blocked'}")
        else:
            status = "OK" if not allowed else "FAIL"
            print(f"   [{status}] Iteration {i+1}: {'Blocked (expected)' if not allowed else 'Allowed (unexpected)'}")
    
    # Test 4: System status
    print("\n4. Testing system status...")
    status = controller.get_system_status()
    print(f"   Health degradation level: {status['health']['degradation_level']}")
    print(f"   Safety counters: {len(status['safety']['counters'])} active")
    
    print("\n" + "=" * 60)
    print("Gold Tier Stability Test Complete!")
    print("=" * 60)
