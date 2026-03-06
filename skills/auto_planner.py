"""
Auto Planner Module

Automatically generates Plan.md files for tasks in Needs_Action/.
Integrates with file_watcher and ralph_loop to ensure every task has execution steps.

Features:
- Auto-detect tasks without plans
- Generate step-by-step execution plans
- Business tasks include accounting steps
- Prevent duplicate plan generation
- Lightweight and hackathon-ready
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Folder paths
NEEDS_ACTION_FOLDER = "Needs_Action"
PLANS_FOLDER = "Plans"

# Business keywords for plan generation
BUSINESS_KEYWORDS = {
    'income': ['client', 'payment', 'revenue', 'sale', 'invoice', 'received', 'customer', 'income'],
    'expense': ['expense', 'cost', 'purchase', 'vendor', 'supplier', 'bill', 'subscription', 'payment'],
    'invoice': ['invoice', 'billing', 'quote', 'estimate', 'proposal', 'payment request'],
    'file_review': ['review', 'read', 'analyze', 'summarize', 'process', 'file']
}


class AutoPlanner:
    """
    Automatically generates execution plans for tasks.
    """
    
    def __init__(self):
        self.plans_generated = 0
        self.ensure_plans_folder()
    
    def ensure_plans_folder(self) -> None:
        """Ensure Plans folder exists."""
        os.makedirs(PLANS_FOLDER, exist_ok=True)
    
    def detect_task_type(self, task_content: str, task_filename: str) -> str:
        """
        Detect task type from content and filename.

        Returns: 'income', 'expense', 'invoice', 'file_review', or 'general'
        """
        content_lower = task_content.lower()
        filename_lower = task_filename.lower()
        combined = content_lower + " " + filename_lower

        # Check for business types first (excluding file_review)
        for task_type, keywords in BUSINESS_KEYWORDS.items():
            if task_type == 'file_review':
                continue  # Check this last
            if any(keyword in combined for keyword in keywords):
                return task_type

        # Check for file review
        for kw in BUSINESS_KEYWORDS['file_review']:
            if kw in combined:
                return 'file_review'

        return 'general'
    
    def generate_steps_for_type(self, task_type: str, task_content: str) -> List[Dict[str, str]]:
        """
        Generate execution steps based on task type.
        
        Returns: List of step dictionaries
        """
        steps = []
        
        if task_type == 'income':
            steps = [
                {"phase": "Phase 1: Preparation", "description": "Read payment details and verify amount"},
                {"phase": "Phase 1: Preparation", "description": "Identify client and payment source"},
                {"phase": "Phase 2: Execution", "description": "Record income in accounting ledger"},
                {"phase": "Phase 2: Execution", "description": "Generate receipt or confirmation"},
                {"phase": "Phase 3: Verification", "description": "Verify accounting entry is correct"},
                {"phase": "Phase 3: Verification", "description": "Mark task as complete"}
            ]
        
        elif task_type == 'expense':
            steps = [
                {"phase": "Phase 1: Preparation", "description": "Read expense details and verify amount"},
                {"phase": "Phase 1: Preparation", "description": "Identify vendor and expense category"},
                {"phase": "Phase 2: Execution", "description": "Record expense in accounting ledger"},
                {"phase": "Phase 2: Execution", "description": "Attach receipt or documentation"},
                {"phase": "Phase 3: Verification", "description": "Verify accounting entry is correct"},
                {"phase": "Phase 3: Verification", "description": "Mark task as complete"}
            ]
        
        elif task_type == 'invoice':
            steps = [
                {"phase": "Phase 1: Preparation", "description": "Read invoice details and amount"},
                {"phase": "Phase 1: Preparation", "description": "Identify client and invoice number"},
                {"phase": "Phase 2: Execution", "description": "Record invoice in accounting ledger"},
                {"phase": "Phase 2: Execution", "description": "Send invoice to client or mark as sent"},
                {"phase": "Phase 3: Verification", "description": "Verify invoice is recorded correctly"},
                {"phase": "Phase 3: Verification", "description": "Mark task as complete"}
            ]
        
        elif task_type == 'file_review':
            steps = [
                {"phase": "Phase 1: Preparation", "description": "Read the file content"},
                {"phase": "Phase 1: Preparation", "description": "Identify key information"},
                {"phase": "Phase 2: Execution", "description": "Summarize main points"},
                {"phase": "Phase 2: Execution", "description": "Create summary document or notes"},
                {"phase": "Phase 3: Verification", "description": "Review summary for completeness"},
                {"phase": "Phase 3: Verification", "description": "Mark task as complete"}
            ]
        
        else:  # general
            steps = [
                {"phase": "Phase 1: Preparation", "description": "Read task requirements"},
                {"phase": "Phase 1: Preparation", "description": "Gather necessary resources"},
                {"phase": "Phase 2: Execution", "description": "Complete the task actions"},
                {"phase": "Phase 2: Execution", "description": "Document results"},
                {"phase": "Phase 3: Verification", "description": "Verify task is complete"},
                {"phase": "Phase 3: Verification", "description": "Mark task as complete"}
            ]
        
        return steps
    
    def extract_task_info(self, task_content: str, task_filename: str) -> Dict[str, Any]:
        """Extract task information for plan generation."""
        info = {
            'filename': task_filename,
            'title': '',
            'description': '',
            'priority': 'medium',
            'related_files': []
        }
        
        # Extract title
        title_match = re.search(r'#\s*Task:\s*(.+)$', task_content, re.MULTILINE)
        if title_match:
            info['title'] = title_match.group(1).strip()
        else:
            info['title'] = task_filename.replace('.md', '')
        
        # Extract description
        desc_match = re.search(r'##\s*Description\s*\n(.+?)(?:\n##|\Z)', task_content, re.DOTALL)
        if desc_match:
            info['description'] = desc_match.group(1).strip()
        
        # Extract priority
        priority_match = re.search(r'Priority:\s*(\w+)', task_content)
        if priority_match:
            info['priority'] = priority_match.group(1)
        
        # Extract related files
        related_match = re.search(r'Related_files:\s*\[(.*?)\]', task_content)
        if related_match:
            files_str = related_match.group(1)
            if files_str.strip():
                info['related_files'] = [f.strip().strip("'\"") for f in files_str.split(',')]
        
        return info
    
    def plan_exists_for_task(self, task_filename: str) -> bool:
        """Check if a plan already exists for this task."""
        if not os.path.exists(PLANS_FOLDER):
            return False
        
        # Look for plan file that references this task
        for filename in os.listdir(PLANS_FOLDER):
            if not filename.endswith('.md'):
                continue
            
            plan_path = os.path.join(PLANS_FOLDER, filename)
            try:
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_content = f.read()
                
                # Check if plan references this task
                if task_filename in plan_content or filename.replace('Plan_', '').replace('.md', '') in task_filename:
                    return True
            except Exception:
                continue
        
        return False
    
    def generate_plan(self, task_filename: str, task_content: str) -> Optional[str]:
        """
        Generate a Plan.md for a task.
        
        Args:
            task_filename: Name of the task file
            task_content: Content of the task file
        
        Returns:
            Path to generated plan file, or None if failed
        """
        # Check if plan already exists
        if self.plan_exists_for_task(task_filename):
            logger.info(f"Plan already exists for {task_filename}")
            return None
        
        # Extract task info
        task_info = self.extract_task_info(task_content, task_filename)
        
        # Detect task type
        task_type = self.detect_task_type(task_content, task_filename)
        
        # Generate steps
        steps = self.generate_steps_for_type(task_type, task_content)
        
        # Generate plan content
        timestamp = datetime.now().isoformat()
        plan_filename = f"Plan_{task_filename}"
        
        plan_content = f"""---
Type: task_plan
Status: pending
Priority: {task_info['priority']}
Created_at: {timestamp}
Source_task: {task_filename}
Related_files: {task_info['related_files']}
Task_type: {task_type}
---

# Plan: {task_info['title']}

## Objective
Complete the task by following the step-by-step actions below.

## Task Summary
- **Source:** `Needs_Action/{task_filename}`
- **Priority:** {task_info['priority']}
- **Created:** {timestamp}
- **Type:** {task_type}
- **Context:** {task_info['description'][:200] if task_info['description'] else 'Task requires execution'}

## Step-by-Step Actions

"""
        
        # Add steps grouped by phase
        current_phase = ""
        for step in steps:
            if step['phase'] != current_phase:
                current_phase = step['phase']
                plan_content += f"### {current_phase}\n"
            
            plan_content += f"- [ ] {step['description']}\n"
        
        plan_content += f"""
## Notes
Auto-generated plan for {task_type} task.
Steps tailored based on task content analysis.
"""
        
        # Write plan file
        plan_path = os.path.join(PLANS_FOLDER, plan_filename)
        try:
            with open(plan_path, 'w', encoding='utf-8') as f:
                f.write(plan_content)
            
            self.plans_generated += 1
            logger.info(f"Generated plan: {plan_filename} (type: {task_type})")
            return plan_path
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            return None
    
    def process_all_pending_tasks(self) -> Dict[str, Any]:
        """
        Process all tasks in Needs_Action/ that don't have plans.
        
        Returns:
            Summary dictionary
        """
        results = {
            'tasks_scanned': 0,
            'plans_generated': 0,
            'plans_skipped': 0,
            'errors': 0
        }
        
        if not os.path.exists(NEEDS_ACTION_FOLDER):
            logger.warning(f"Needs_Action folder not found: {NEEDS_ACTION_FOLDER}")
            return results
        
        for filename in os.listdir(NEEDS_ACTION_FOLDER):
            if not filename.endswith('.md'):
                continue
            
            results['tasks_scanned'] += 1
            task_path = os.path.join(NEEDS_ACTION_FOLDER, filename)
            
            try:
                with open(task_path, 'r', encoding='utf-8') as f:
                    task_content = f.read()
                
                plan_path = self.generate_plan(filename, task_content)
                
                if plan_path:
                    results['plans_generated'] += 1
                else:
                    results['plans_skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing task {filename}: {e}")
                results['errors'] += 1
        
        return results


# ============================================================
# Convenience Functions
# ============================================================

_auto_planner = None

def get_auto_planner() -> AutoPlanner:
    """Get or create auto planner instance."""
    global _auto_planner
    if _auto_planner is None:
        _auto_planner = AutoPlanner()
    return _auto_planner


def generate_plan_for_task(task_filename: str, task_content: str) -> Optional[str]:
    """Generate a plan for a specific task."""
    planner = get_auto_planner()
    return planner.generate_plan(task_filename, task_content)


def process_pending_tasks() -> Dict[str, Any]:
    """Process all pending tasks and generate plans."""
    planner = get_auto_planner()
    return planner.process_all_pending_tasks()


def ensure_plan_exists(task_filename: str, task_content: str) -> bool:
    """
    Ensure a plan exists for a task. Generate if missing.
    
    Args:
        task_filename: Task filename
        task_content: Task content
    
    Returns:
        True if plan exists (or was created), False if failed
    """
    planner = get_auto_planner()
    
    # Check if plan exists
    if planner.plan_exists_for_task(task_filename):
        return True
    
    # Generate plan
    plan_path = planner.generate_plan(task_filename, task_content)
    return plan_path is not None


# ============================================================
# Integration with File Watcher
# ============================================================

def on_task_created(task_filename: str, task_content: str) -> None:
    """
    Called when a new task is created.
    Automatically generates a plan.
    
    Args:
        task_filename: Name of created task
        task_content: Content of created task
    """
    logger.info(f"Task created: {task_filename} - generating plan...")
    plan_path = generate_plan_for_task(task_filename, task_content)
    
    if plan_path:
        logger.info(f"Plan generated: {plan_path}")
    else:
        logger.warning(f"Plan generation skipped for: {task_filename}")


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Auto Planner - Generate Plans for Pending Tasks")
    print("=" * 60)
    
    planner = get_auto_planner()
    results = planner.process_all_pending_tasks()
    
    print(f"\nResults:")
    print(f"  Tasks scanned: {results['tasks_scanned']}")
    print(f"  Plans generated: {results['plans_generated']}")
    print(f"  Plans skipped (already exist): {results['plans_skipped']}")
    print(f"  Errors: {results['errors']}")
    
    print("\n" + "=" * 60)
