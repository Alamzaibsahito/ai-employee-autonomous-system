"""
Error Recovery Integration Test

Tests error recovery integration with existing components.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.error_recovery import (
    ErrorRecovery,
    get_system_health,
    with_error_recovery,
)
from skills.error_recovery_wrapper import (
    safe_execute,
    wrap_accounting_update,
    wrap_task_processor,
    wrap_mcp_call,
)

print("=" * 60)
print("Error Recovery Integration Tests")
print("=" * 60)

# Test 1: Wrap accounting update
print("\n1. Testing wrapped accounting update...")

def test_accounting():
    return {"success": True, "amount": 100, "entry": "test"}

safe_func = wrap_accounting_update(test_accounting)
result = safe_func()
print(f"   Result: {result}")

# Test 2: Wrap task processor
print("\n2. Testing wrapped task processor...")

def test_task_processor():
    return {"status": "processed", "task": "test_task"}

safe_task = wrap_task_processor(test_task_processor)
result = safe_task()
print(f"   Result: {result}")

# Test 3: Wrap MCP call
print("\n3. Testing wrapped MCP call...")

def test_mcp_call():
    return {"success": True, "response": "MCP response"}

safe_mcp = wrap_mcp_call(test_mcp_call)
result = safe_mcp()
print(f"   Result: {result}")

# Test 4: Error handling in wrapped function
print("\n4. Testing error handling in wrapped function...")

def failing_function():
    raise ConnectionError("Simulated connection failure")

safe_failing = wrap_task_processor(failing_function)
result = safe_failing()
print(f"   Result (error response): {result}")
print(f"   Success flag: {result.get('success', False)}")

# Test 5: System health tracking
print("\n5. Testing system health tracking...")

health = get_system_health()
print(f"   Initial degradation level: {health.get_degradation_level()}")

# Mark a component unhealthy
health.mark_unhealthy("test_component", Exception("Test error"))
print(f"   After error - degradation level: {health.get_degradation_level()}")
print(f"   Component status: {health.component_status.get('test_component')}")

# Test 6: Decorator usage
print("\n6. Testing decorator usage...")

@with_error_recovery(component="test_component", action_type="test", max_retries=2)
def decorated_operation():
    return "Operation completed successfully"

result = decorated_operation()
print(f"   Result: {result}")

# Test 7: Safe execute with default
print("\n7. Testing safe_execute with default return...")

def risky_op():
    raise ValueError("Risky operation failed")

result = safe_execute(
    risky_op,
    component="test",
    action="risky_operation",
    default_return={"status": "fallback", "recovered": True}
)
print(f"   Result: {result}")

# Test 8: Verify error log was written
print("\n8. Verifying error log...")

import os
log_path = "Logs/error_recovery.log"
if os.path.exists(log_path):
    with open(log_path, 'r') as f:
        lines = f.readlines()
    print(f"   Error log exists with {len(lines)} entries")
    print(f"   Latest entry: {lines[-1].strip()[:80]}...")
else:
    print("   Error log not found!")

print("\n" + "=" * 60)
print("All integration tests complete!")
print("=" * 60)
