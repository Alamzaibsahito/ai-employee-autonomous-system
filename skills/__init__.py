# Skills module for hackathon-0
# Provides reusable skills for the AI Employee system

from .error_recovery import (
    ErrorRecovery,
    ErrorCategory,
    ErrorRecoveryError,
    TransientError,
    AuthenticationError,
    LogicError,
    DataError,
    SystemError,
    with_error_recovery,
    safe_watcher_operation,
    safe_task_processing,
    safe_mcp_call,
    safe_accounting_update,
    safe_report_generation,
    handle_error_gracefully,
    retry_on_transient_error,
    get_system_health,
    SystemHealth,
)

from .ralph_loop import (
    RalphLoop,
    PlanParser,
    StepExecutor,
    TaskVerifier,
    run_ralph_loop,
    run_ralph_loop_continuous,
)

from .auto_planner import (
    AutoPlanner,
    get_auto_planner,
    generate_plan_for_task,
    process_pending_tasks,
    ensure_plan_exists,
    on_task_created,
)

from .gold_stability import (
    GoldTierStability,
    GracefulDegradation,
    CrossDomainIntegration,
    SafetyChecks,
    SchedulerStability,
    get_stability_controller,
    safe_mcp_call,
    detect_business_intent,
    auto_trigger_accounting,
)

__all__ = [
    # Error Recovery
    "ErrorRecovery",
    "ErrorCategory",
    "ErrorRecoveryError",
    "TransientError",
    "AuthenticationError",
    "LogicError",
    "DataError",
    "SystemError",
    "with_error_recovery",
    "safe_watcher_operation",
    "safe_task_processing",
    "safe_mcp_call",
    "safe_accounting_update",
    "safe_report_generation",
    "handle_error_gracefully",
    "retry_on_transient_error",
    "get_system_health",
    "SystemHealth",
    # Ralph Loop
    "RalphLoop",
    "PlanParser",
    "StepExecutor",
    "TaskVerifier",
    "run_ralph_loop",
    "run_ralph_loop_continuous",
    # Auto Planner
    "AutoPlanner",
    "get_auto_planner",
    "generate_plan_for_task",
    "process_pending_tasks",
    "ensure_plan_exists",
    "on_task_created",
    # Gold Stability
    "GoldTierStability",
    "GracefulDegradation",
    "CrossDomainIntegration",
    "SafetyChecks",
    "SchedulerStability",
    "get_stability_controller",
    "detect_business_intent",
    "auto_trigger_accounting",
]
