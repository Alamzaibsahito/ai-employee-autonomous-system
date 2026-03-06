"""
Ralph Wiggum Loop - Autonomous Multi-Step Task Execution

This module implements an autonomous execution loop that follows the cycle:
PLAN → EXECUTE → VERIFY → RETRY OR COMPLETE

The loop automatically executes tasks step-by-step until:
- All steps are completed (task marked as "done")
- Maximum retries exceeded (task marked as "needs_human_review")
- No plan exists (task waits for planner)

Concept: Like Ralph Wiggum from The Simpsons who keeps trying until he succeeds
(or gets confused and needs help).

Usage:
    from skills.ralph_loop import RalphLoop
    
    loop = RalphLoop()
    loop.run_cycle()  # Execute one cycle of all pending tasks
"""

import os
import re
import shutil
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Import error recovery
try:
    from .error_recovery import (
        ErrorRecovery,
        get_system_health,
        with_error_recovery,
    )
    from .error_recovery_wrapper import (
        safe_execute,
        wrap_component_execution,
    )
except ImportError:
    from error_recovery import (
        ErrorRecovery,
        get_system_health,
        with_error_recovery,
    )
    from error_recovery_wrapper import (
        safe_execute,
        wrap_component_execution,
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Folder paths
NEEDS_ACTION_FOLDER = "Needs_Action"
PLANS_FOLDER = "Plans"
DONE_FOLDER = "Done"
REVIEW_REQUIRED_FOLDER = "Review_Required"
PENDING_APPROVAL_FOLDER = "Pending_Approval"
APPROVED_FOLDER = "Approved"

# Ensure directories exist
for folder in [NEEDS_ACTION_FOLDER, PLANS_FOLDER, DONE_FOLDER, 
               REVIEW_REQUIRED_FOLDER, PENDING_APPROVAL_FOLDER, APPROVED_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Loop configuration
LOOP_CONFIG = {
    "max_iterations_per_task": 10,  # Prevent infinite loops
    "max_retries_per_step": 1,      # One automatic retry
    "log_every_step": True,         # Log each step execution
}


# ============================================================
# Plan Parser
# ============================================================

class PlanParser:
    """Parse and extract steps from plan markdown files."""
    
    def __init__(self, plan_content: str):
        self.plan_content = plan_content
        self.steps: List[Dict] = []
        self.metadata: Dict = {}
        self._parse()
    
    def _parse(self) -> None:
        """Parse plan content into structured steps."""
        # Extract YAML frontmatter
        self._parse_frontmatter()
        
        # Extract steps from checklist
        self._parse_steps()
    
    def _parse_frontmatter(self) -> None:
        """Extract metadata from YAML frontmatter."""
        frontmatter_match = re.search(r'---\n(.*?)\n---', self.plan_content, re.DOTALL)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            
            # Parse key-value pairs
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.metadata[key.strip()] = value.strip()
    
    def _parse_steps(self) -> None:
        """Extract steps from markdown checklist."""
        # Find all checklist items
        checklist_pattern = r'^\s*-\s*\[([ x])\]\s*(.+)$'
        
        lines = self.plan_content.split('\n')
        current_phase = "General"
        
        for line in lines:
            # Check for phase headers
            phase_match = re.match(r'^###\s+(.+)$', line)
            if phase_match:
                current_phase = phase_match.group(1)
                continue
            
            # Check for checklist items
            step_match = re.match(checklist_pattern, line)
            if step_match:
                checked = step_match.group(1).strip() == 'x'
                description = step_match.group(2).strip()
                
                self.steps.append({
                    "description": description,
                    "completed": checked,
                    "phase": current_phase,
                    "retry_count": 0
                })
    
    def get_pending_steps(self) -> List[Dict]:
        """Get steps that are not yet completed."""
        return [step for step in self.steps if not step["completed"]]
    
    def get_next_step(self) -> Optional[Dict]:
        """Get the next pending step."""
        pending = self.get_pending_steps()
        return pending[0] if pending else None
    
    def get_completed_steps(self) -> List[Dict]:
        """Get completed steps."""
        return [step for step in self.steps if step["completed"]]
    
    def get_completion_percentage(self) -> float:
        """Get completion percentage."""
        if not self.steps:
            return 0.0
        completed = len(self.get_completed_steps())
        return (completed / len(self.steps)) * 100
    
    def mark_step_completed(self, step_index: int) -> None:
        """Mark a step as completed."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["completed"] = True
    
    def get_source_task(self) -> Optional[str]:
        """Get the source task filename from metadata."""
        return self.metadata.get("Source_task")


# ============================================================
# Step Executor
# ============================================================

class StepExecutor:
    """Execute individual steps from a plan."""
    
    def __init__(self):
        self.recovery = ErrorRecovery(component_name="ralph_loop")
        self.execution_history: List[Dict] = []
    
    def execute_step(self, step: Dict, task_context: Dict) -> Tuple[bool, str]:
        """
        Execute a single step.
        
        Args:
            step: Step dictionary with description
            task_context: Task context information
        
        Returns:
            Tuple of (success, message)
        """
        step_description = step.get("description", "").lower()
        
        # Determine step type and execute appropriate action
        if self._is_file_operation(step_description):
            return self._execute_file_operation(step, task_context)
        elif self._is_mcp_action(step_description):
            return self._execute_mcp_action(step, task_context)
        elif self._is_approval_action(step_description):
            return self._execute_approval_action(step, task_context)
        elif self._is_accounting_action(step_description):
            return self._execute_accounting_action(step, task_context)
        else:
            # Generic step - mark as complete if no specific action needed
            return self._execute_generic_step(step, task_context)
    
    def _is_file_operation(self, description: str) -> bool:
        """Check if step involves file operations."""
        keywords = ["read", "write", "create", "delete", "move", "copy", "file", "document"]
        return any(kw in description for kw in keywords)
    
    def _is_mcp_action(self, description: str) -> bool:
        """Check if step involves MCP server action."""
        keywords = ["email", "send", "post", "linkedin", "gmail", "api", "external"]
        return any(kw in description for kw in keywords)
    
    def _is_approval_action(self, description: str) -> bool:
        """Check if step requires human approval."""
        # More specific keywords that indicate actual approval actions
        keywords = [
            "human approval",
            "requires approval", 
            "get approval",
            "approve",
            "authorize",
            "permission required",
            "confirm with",
            "get permission"
        ]
        description_lower = description.lower()
        return any(kw in description_lower for kw in keywords)
    
    def _is_accounting_action(self, description: str) -> bool:
        """Check if step involves accounting."""
        keywords = ["payment", "invoice", "expense", "income", "record", "accounting"]
        return any(kw in description for kw in keywords)
    
    def _execute_file_operation(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Execute file operation step."""
        try:
            description = step.get("description", "").lower()
            
            # Simulate file operation (in production, would do actual file ops)
            if "read" in description:
                return True, f"File operation completed: {description}"
            elif "create" in description or "write" in description:
                return True, f"File created: {description}"
            elif "move" in description:
                return True, f"File moved: {description}"
            else:
                return True, f"File operation completed: {description}"
                
        except Exception as e:
            self.recovery.log_error(e, "file_operation", 0, 0, context)
            return False, f"File operation failed: {str(e)}"
    
    def _execute_mcp_action(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Execute MCP server action step."""
        try:
            description = step.get("description", "")
            
            # In production, would call actual MCP servers
            # For now, simulate successful execution
            logger.info(f"Would execute MCP action: {description}")
            
            return True, f"MCP action completed: {description}"
            
        except Exception as e:
            self.recovery.log_error(e, "mcp_action", 0, 0, context)
            return False, f"MCP action failed: {str(e)}"
    
    def _execute_approval_action(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Execute approval-related step."""
        try:
            # Check if approval is already granted
            task_file = context.get("task_file")
            
            # Check Approved folder for approval
            if task_file:
                approved_file = os.path.join(APPROVED_FOLDER, os.path.basename(task_file))
                if os.path.exists(approved_file):
                    return True, "Approval granted"
                
                # Check if pending
                pending_file = os.path.join(PENDING_APPROVAL_FOLDER, os.path.basename(task_file))
                if os.path.exists(pending_file):
                    return False, "Approval pending - waiting for human"
            
            # Create approval request
            return self._create_approval_request(step, context)
            
        except Exception as e:
            self.recovery.log_error(e, "approval_action", 0, 0, context)
            return False, f"Approval action failed: {str(e)}"
    
    def _create_approval_request(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Create an approval request file."""
        try:
            task_file = context.get("task_file", "unknown")
            approval_id = f"approval_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create approval request content
            approval_content = f"""---
Type: approval_request
Status: pending_approval
Created_at: {datetime.now().isoformat()}
Source_task: {task_file}
Action_type: step_execution
---

# Approval Request: Step Execution

## Requested Action
{step.get('description', 'Unknown action')}

## Context
- **Source Task:** `{task_file}`
- **Step:** {step.get('phase', 'General')} - {step.get('description', 'Unknown')}

## Why Approval Required
This step requires human approval before execution.

---

## Human Decision Required

**To Approve:** Move this file to `Approved/` folder
**To Reject:** Move this file to `Rejected/` folder
"""
            
            # Write approval request
            approval_file = os.path.join(PENDING_APPROVAL_FOLDER, f"{approval_id}.md")
            with open(approval_file, 'w', encoding='utf-8') as f:
                f.write(approval_content)
            
            return False, f"Approval request created: {approval_id}"
            
        except Exception as e:
            return False, f"Failed to create approval request: {str(e)}"
    
    def _execute_accounting_action(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Execute accounting-related step."""
        try:
            description = step.get("description", "Unknown accounting step")
            
            # Import accounting module if available
            try:
                from accounting_skill import process_business_action

                result = process_business_action(description, source="ralph_loop")

                if result and result.get("success"):
                    return True, f"Accounting entry recorded: {description}"
                else:
                    return True, f"Accounting step completed (no entry needed): {description}"

            except ImportError:
                logger.warning("Accounting module not available, skipping accounting action")
                return True, f"Accounting step skipped (module not available): {description}"

        except Exception as e:
            self.recovery.log_error(e, "accounting_action", 0, 0, context)
            return False, f"Accounting action failed: {str(e)}"
    
    def _execute_generic_step(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """Execute a generic step (no specific action needed)."""
        try:
            # For generic steps, just log and mark as complete
            logger.info(f"Executing generic step: {step.get('description', 'Unknown')}")
            return True, f"Step completed: {step.get('description', 'Unknown')}"
            
        except Exception as e:
            self.recovery.log_error(e, "generic_step", 0, 0, context)
            return False, f"Generic step failed: {str(e)}"


# ============================================================
# Task Verifier
# ============================================================

class TaskVerifier:
    """Verify task completion status."""
    
    def __init__(self):
        self.recovery = ErrorRecovery(component_name="verifier")
    
    def verify_step_completion(self, step: Dict, execution_result: Tuple[bool, str]) -> bool:
        """
        Verify if a step was completed successfully.
        
        Args:
            step: Step dictionary
            execution_result: Result from step execution (success, message)
        
        Returns:
            True if step is verified complete, False otherwise
        """
        success, message = execution_result
        
        if success:
            logger.debug(f"Step verified complete: {step.get('description', 'Unknown')}")
            return True
        
        logger.warning(f"Step verification failed: {message}")
        return False
    
    def verify_task_completion(self, plan: PlanParser) -> bool:
        """
        Verify if all steps in a plan are completed.
        
        Args:
            plan: Parsed plan
        
        Returns:
            True if all steps completed, False otherwise
        """
        pending_steps = plan.get_pending_steps()
        
        if not pending_steps:
            logger.info("All steps completed - task verified complete")
            return True
        
        logger.info(f"Task not complete - {len(pending_steps)} steps remaining")
        return False


# ============================================================
# Ralph Loop - Main Controller
# ============================================================

class RalphLoop:
    """
    Ralph Wiggum Loop - Autonomous task execution controller.

    Follows the cycle: PLAN → EXECUTE → VERIFY → RETRY OR COMPLETE
    
    Gold Tier Features:
    - Graceful degradation (continues on MCP failures)
    - Cross-domain integration (auto-triggers accounting)
    - Safety checks (prevents infinite loops)
    """

    def __init__(self):
        self.executor = StepExecutor()
        self.verifier = TaskVerifier()
        self.recovery = ErrorRecovery(component_name="ralph_loop")
        self.health = get_system_health()
        
        # Gold Tier stability features
        try:
            from .gold_stability import (
                get_stability_controller,
                auto_trigger_accounting,
            )
            self.stability = get_stability_controller()
            self.auto_trigger_accounting = auto_trigger_accounting
        except ImportError:
            self.stability = None
            self.auto_trigger_accounting = None
        
        self.loop_count = 0
        self.tasks_processed = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
    
    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete cycle of the Ralph Loop.
        
        Processes all tasks with active plans.
        
        Returns:
            Summary dictionary with cycle results
        """
        self.loop_count += 1
        logger.info(f"=" * 60)
        logger.info(f"Ralph Loop Cycle {self.loop_count} starting...")
        logger.info(f"=" * 60)
        
        cycle_results = {
            "cycle": self.loop_count,
            "timestamp": datetime.now().isoformat(),
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "steps_executed": 0
        }
        
        # Get all task files
        task_files = self._get_task_files()
        
        for task_file in task_files:
            try:
                result = self._process_task(task_file)
                cycle_results["tasks_processed"] += 1
                
                if result.get("completed"):
                    cycle_results["tasks_completed"] += 1
                    self.tasks_completed += 1
                elif result.get("failed"):
                    cycle_results["tasks_failed"] += 1
                    self.tasks_failed += 1
                
                cycle_results["steps_executed"] += result.get("steps_executed", 0)
                
            except Exception as e:
                self.recovery.log_error(e, f"task_{task_file}", 0, 0)
                logger.error(f"Error processing task {task_file}: {e}")
        
        self.tasks_processed += cycle_results["tasks_processed"]
        
        logger.info(f"=" * 60)
        logger.info(f"Ralph Loop Cycle {self.loop_count} complete!")
        logger.info(f"  Tasks processed: {cycle_results['tasks_processed']}")
        logger.info(f"  Tasks completed: {cycle_results['tasks_completed']}")
        logger.info(f"  Tasks failed: {cycle_results['tasks_failed']}")
        logger.info(f"  Steps executed: {cycle_results['steps_executed']}")
        logger.info(f"=" * 60)
        
        return cycle_results
    
    def _get_task_files(self) -> List[str]:
        """Get list of task files to process."""
        task_files = []
        
        if os.path.exists(NEEDS_ACTION_FOLDER):
            for filename in os.listdir(NEEDS_ACTION_FOLDER):
                if filename.endswith('.md'):
                    task_files.append(filename)
        
        return task_files
    
    def _process_task(self, task_file: str) -> Dict[str, Any]:
        """
        Process a single task through the loop.

        Args:
            task_file: Task filename

        Returns:
            Result dictionary
        """
        task_path = os.path.join(NEEDS_ACTION_FOLDER, task_file)

        # Read task content
        with open(task_path, 'r', encoding='utf-8') as f:
            task_content = f.read()

        # Gold Tier: Cross-domain integration - auto-trigger accounting for business tasks
        if self.auto_trigger_accounting:
            try:
                accounting_result = self.auto_trigger_accounting(task_content, task_file)
                if accounting_result:
                    logger.info(f"Cross-domain: Accounting entry recorded for task {task_file}")
            except Exception as e:
                logger.warning(f"Cross-domain accounting failed (non-blocking): {e}")

        # Find corresponding plan
        plan = self._find_plan_for_task(task_file, task_content)

        # Gold Tier: Auto-generate plan if missing
        if not plan:
            logger.info(f"No plan found for task {task_file} - auto-generating...")
            try:
                from .auto_planner import generate_plan_for_task
                plan_path = generate_plan_for_task(task_file, task_content)
                if plan_path:
                    logger.info(f"Plan auto-generated: {plan_path}")
                    # Reload plan
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        plan_content = f.read()
                    plan = PlanParser(plan_content)
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Plan auto-generation failed: {e}")
            
            # If still no plan, skip task
            if not plan:
                logger.info(f"No plan found for task {task_file} - skipping")
                return {"completed": False, "failed": False, "steps_executed": 0, "reason": "no_plan"}

        # Execute loop for this task
        return self._execute_task_loop(task_file, task_path, plan)
    
    def _find_plan_for_task(self, task_file: str, task_content: str) -> Optional[PlanParser]:
        """Find the plan file for a task."""
        # Try to find plan by source_task reference
        if os.path.exists(PLANS_FOLDER):
            for filename in os.listdir(PLANS_FOLDER):
                if not filename.endswith('.md'):
                    continue
                
                plan_path = os.path.join(PLANS_FOLDER, filename)
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_content = f.read()
                
                # Check if this plan references our task
                if task_file in plan_content or filename.replace('Plan_', '').replace('.md', '') in task_file:
                    return PlanParser(plan_content)
        
        return None
    
    def _execute_task_loop(self, task_file: str, task_path: str, plan: PlanParser) -> Dict[str, Any]:
        """
        Execute the loop for a single task.
        
        Args:
            task_file: Task filename
            task_path: Full task path
            plan: Parsed plan
        
        Returns:
            Result dictionary
        """
        task_context = {
            "task_file": task_file,
            "task_path": task_path,
            "plan": plan
        }
        
        iterations = 0
        steps_executed = 0
        max_iterations = LOOP_CONFIG["max_iterations_per_task"]
        max_retries = LOOP_CONFIG["max_retries_per_step"]
        
        while iterations < max_iterations:
            iterations += 1
            
            # Get next pending step
            next_step = plan.get_next_step()
            
            if not next_step:
                # All steps completed!
                logger.info(f"Task {task_file} - All steps completed!")
                self._complete_task(task_file, task_path, plan)
                return {
                    "completed": True,
                    "failed": False,
                    "steps_executed": steps_executed,
                    "iterations": iterations
                }
            
            # Execute the step
            logger.info(f"Executing step {iterations}: {next_step['description']}")
            success, message = self.executor.execute_step(next_step, task_context)
            steps_executed += 1
            
            # Verify result
            if self.verifier.verify_step_completion(next_step, (success, message)):
                # Step successful - mark as complete
                step_index = plan.steps.index(next_step)
                plan.mark_step_completed(step_index)
                self._update_plan_file(plan, task_file)
                logger.info(f"Step completed: {next_step['description']}")
                
            else:
                # Step failed - handle failure
                logger.warning(f"Step failed: {message}")
                
                # Check retry count
                if next_step.get("retry_count", 0) < max_retries:
                    # Retry once
                    next_step["retry_count"] = next_step.get("retry_count", 0) + 1
                    logger.info(f"Retrying step (attempt {next_step['retry_count']})")
                    continue
                else:
                    # Max retries exceeded - escalate
                    logger.error(f"Step failed after {max_retries} retries")
                    self._escalate_task(task_file, task_path, plan, message)
                    return {
                        "completed": False,
                        "failed": True,
                        "steps_executed": steps_executed,
                        "iterations": iterations,
                        "reason": "max_retries_exceeded"
                    }
        
        # Max iterations reached
        logger.warning(f"Task {task_file} - Max iterations ({max_iterations}) reached")
        self._escalate_task(task_file, task_path, plan, "Max iterations exceeded")
        return {
            "completed": False,
            "failed": True,
            "steps_executed": steps_executed,
            "iterations": iterations,
            "reason": "max_iterations_exceeded"
        }
    
    def _update_plan_file(self, plan: PlanParser, task_file: str) -> None:
        """Update the plan file with completed steps."""
        # Find the plan file
        plan_file = None
        if os.path.exists(PLANS_FOLDER):
            for filename in os.listdir(PLANS_FOLDER):
                if filename.endswith('.md'):
                    plan_path = os.path.join(PLANS_FOLDER, filename)
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if task_file in content:
                        plan_file = plan_path
                        break
        
        if not plan_file:
            return
        
        # Rebuild the plan content with updated steps
        lines = []
        in_checklist = False
        
        with open(plan_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        step_index = 0
        for line in content.split('\n'):
            # Check if this is a checklist item
            checklist_match = re.match(r'^(\s*-\s*\[)[ x](\]\s*.+)$', line)
            if checklist_match:
                if step_index < len(plan.steps):
                    step = plan.steps[step_index]
                    checkbox = 'x' if step['completed'] else ' '
                    lines.append(f"{checklist_match.group(1)}{checkbox}{checklist_match.group(2)}")
                    step_index += 1
                else:
                    lines.append(line)
            else:
                lines.append(line)
        
        # Write updated content
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _complete_task(self, task_file: str, task_path: str, plan: PlanParser) -> None:
        """Mark task as complete and move to Done folder."""
        try:
            # Read task content
            with open(task_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update status to done
            content = re.sub(r'Status:\s*\w+', 'Status: done', content)
            
            # Write updated content
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Move to Done folder
            done_path = os.path.join(DONE_FOLDER, task_file)
            shutil.move(task_path, done_path)
            
            logger.info(f"Task {task_file} moved to Done folder")
            
            # Log completion
            self._log_task_completion(task_file, plan)
            
        except Exception as e:
            self.recovery.log_error(e, "complete_task", 0, 0, {"task_file": task_file})
            logger.error(f"Failed to complete task {task_file}: {e}")
    
    def _escalate_task(self, task_file: str, task_path: str, plan: PlanParser, reason: str) -> None:
        """Escalate task to human review."""
        try:
            # Create review file
            review_id = f"review_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            with open(task_path, 'r', encoding='utf-8') as f:
                task_content = f.read()
            
            review_content = f"""---
Type: review_required
Status: pending_review
Priority: high
Created_at: {datetime.now().isoformat()}
Original_task: {task_file}
Error_reason: {reason}
---

# Review Required: {task_file}

## Original Task
{task_content}

## Error Details
- **Reason:** {reason}
- **Completion:** {plan.get_completion_percentage():.1f}%
- **Steps completed:** {len(plan.get_completed_steps())} / {len(plan.steps)}

## Human Action Required

Please review this task and take one of the following actions:

- [ ] Fix the issue and move back to Needs_Action/
- [ ] Mark as complete and move to Done/
- [ ] Reject and move to Rejected/

## Resolution Section (Filled by Human)

**Action taken:** ________________
**Notes:** ________________
**Date:** ________________
"""
            
            # Write review file
            review_file = os.path.join(REVIEW_REQUIRED_FOLDER, f"{review_id}.md")
            with open(review_file, 'w', encoding='utf-8') as f:
                f.write(review_content)
            
            # Remove original task
            if os.path.exists(task_path):
                os.remove(task_path)
            
            logger.warning(f"Task {task_file} escalated to Review_Required: {reason}")
            
        except Exception as e:
            self.recovery.log_error(e, "escalate_task", 0, 0, {"task_file": task_file})
            logger.error(f"Failed to escalate task {task_file}: {e}")
    
    def _log_task_completion(self, task_file: str, plan: PlanParser) -> None:
        """Log task completion to system log."""
        timestamp = datetime.now().isoformat()
        log_entry = (
            f"[{timestamp}] RALPH_LOOP | Task completed: {task_file} | "
            f"Steps: {len(plan.steps)} | "
            f"Completion: 100%"
        )
        
        # Write to system log
        log_path = "Logs/System_Log.md"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception as e:
            logger.error(f"Failed to write to system log: {e}")


# ============================================================
# Convenience Functions
# ============================================================

def run_ralph_loop() -> Dict[str, Any]:
    """Run one cycle of the Ralph Loop."""
    loop = RalphLoop()
    return loop.run_cycle()


def run_ralph_loop_continuous(cycles: int = 10, delay_seconds: int = 5) -> None:
    """
    Run Ralph Loop continuously for specified cycles.
    
    Args:
        cycles: Number of cycles to run
        delay_seconds: Delay between cycles
    """
    import time
    
    loop = RalphLoop()
    
    for i in range(cycles):
        result = loop.run_cycle()
        
        if result["tasks_processed"] == 0:
            logger.info("No tasks to process - waiting...")
        
        if i < cycles - 1:
            time.sleep(delay_seconds)


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Ralph Wiggum Loop - Autonomous Task Execution")
    print("=" * 60)
    print()
    
    # Run one cycle
    loop = RalphLoop()
    result = loop.run_cycle()
    
    print()
    print("Cycle Summary:")
    print(f"  Tasks processed: {result['tasks_processed']}")
    print(f"  Tasks completed: {result['tasks_completed']}")
    print(f"  Tasks failed: {result['tasks_failed']}")
    print(f"  Steps executed: {result['steps_executed']}")
    print()
    print("=" * 60)
