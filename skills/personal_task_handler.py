"""
Personal Task Handler Skill

Enables the AI Employee to separate personal tasks from business tasks.
Personal tasks are routed to AI_Employee_Vault/personal/ while business tasks
go to the main vault structure.

This skill integrates with:
- Ralph Loop for task execution
- Scheduler for timed tasks
- Error Recovery for graceful handling

Usage:
    from skills.personal_task_handler import PersonalTaskHandler
    
    handler = PersonalTaskHandler()
    
    # Detect task type
    task_type = handler.detect_task_type(task_content)
    
    # Route personal task
    if task_type == "personal":
        handler.route_personal_task(task_file, task_content)
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================

# Folder paths
PERSONAL_VAULT = "AI_Employee_Vault/personal"
PERSONAL_TASKS_FOLDER = os.path.join(PERSONAL_VAULT, "tasks")
PERSONAL_PLANS_FOLDER = os.path.join(PERSONAL_VAULT, "plans")
PERSONAL_LOGS_FOLDER = os.path.join(PERSONAL_VAULT, "logs")

# Business folders (for comparison)
BUSINESS_TASKS_FOLDER = "Needs_Action"
BUSINESS_DONE_FOLDER = "Done"

# Log files
PERSONAL_LOG_FILE = os.path.join(PERSONAL_LOGS_FOLDER, "personal_log.md")
SYSTEM_LOG_FILE = "Logs/System_Log.md"

# Ensure directories exist
for folder in [PERSONAL_TASKS_FOLDER, PERSONAL_PLANS_FOLDER, PERSONAL_LOGS_FOLDER]:
    os.makedirs(folder, exist_ok=True)


# ============================================================
# Personal Task Detection
# ============================================================

class PersonalTaskDetector:
    """Detects whether a task is personal or business-related."""
    
    # Keywords that indicate personal tasks
    PERSONAL_KEYWORDS = [
        # Family & Relationships
        'family', 'spouse', 'children', 'kids', 'parents', 'siblings',
        'anniversary', 'birthday', 'wedding', 'graduation',
        
        # Personal Health
        'doctor', 'dentist', 'medical', 'health', 'exercise', 'gym',
        'workout', 'meditation', 'therapy', 'appointment',
        
        # Personal Finance
        'personal budget', 'personal savings', 'personal investment',
        'mortgage', 'rent payment', 'utility bill',
        
        # Home & Living
        'grocery', 'shopping', 'cleaning', 'laundry', 'cooking',
        'home repair', 'maintenance', 'garden', 'yard',
        
        # Personal Development
        'hobby', 'reading', 'learning', 'course', 'personal project',
        'meditation', 'mindfulness',
        
        # Travel & Leisure
        'vacation', 'holiday', 'trip', 'travel', 'flight', 'hotel',
        'restaurant', 'movie', 'concert', 'event',
        
        # Personal Admin
        'personal email', 'personal phone', 'license renewal',
        'insurance', 'personal tax',
        
        # Vehicles
        'car maintenance', 'oil change', 'car wash', 'vehicle',
        
        # Pets
        'pet', 'dog', 'cat', 'vet', 'pet food', 'pet care'
    ]
    
    # Keywords that indicate business tasks
    BUSINESS_KEYWORDS = [
        'client', 'customer', 'invoice', 'payment received', 'revenue',
        'business', 'company', 'corporation', 'LLC', 'inc',
        'meeting', 'presentation', 'proposal', 'contract',
        'marketing', 'sales', 'lead', 'prospect',
        'employee', 'team', 'hire', 'recruit',
        'product', 'service', 'launch', 'release',
        'accounting', 'tax', 'audit', 'compliance',
        'social media', 'post', 'tweet', 'linkedin', 'facebook',
        'email campaign', 'newsletter', 'subscriber'
    ]
    
    def __init__(self):
        self.personal_score = 0
        self.business_score = 0
    
    def detect_task_type(self, task_content: str) -> str:
        """
        Detect whether a task is personal or business.
        
        Args:
            task_content: Task content to analyze
            
        Returns:
            'personal', 'business', or 'mixed'
        """
        task_lower = task_content.lower()
        
        self.personal_score = 0
        self.business_score = 0
        
        # Count personal keywords
        for keyword in self.PERSONAL_KEYWORDS:
            if keyword in task_lower:
                self.personal_score += 1
        
        # Count business keywords
        for keyword in self.BUSINESS_KEYWORDS:
            if keyword in task_lower:
                self.business_score += 1
        
        # Determine task type
        if self.personal_score > 0 and self.business_score == 0:
            return 'personal'
        elif self.business_score > 0 and self.personal_score == 0:
            return 'business'
        elif self.personal_score > self.business_score:
            return 'personal'
        elif self.business_score > self.personal_score:
            return 'business'
        else:
            return 'mixed'
    
    def get_confidence(self) -> float:
        """
        Get confidence score for the detection.
        
        Returns:
            Confidence score between 0 and 1
        """
        total = self.personal_score + self.business_score
        if total == 0:
            return 0.5  # Neutral if no keywords found
        
        max_score = max(self.personal_score, self.business_score)
        return max_score / total


# ============================================================
# Personal Task Handler
# ============================================================

class PersonalTaskHandler:
    """
    Handles personal task routing and management.
    
    Features:
    - Detect personal vs business tasks
    - Route personal tasks to personal vault
    - Log personal task activity
    - Integrate with Ralph Loop
    """
    
    def __init__(self):
        self.detector = PersonalTaskDetector()
        self._ensure_personal_structure()
    
    def _ensure_personal_structure(self):
        """Ensure personal vault folder structure exists."""
        for folder in [PERSONAL_TASKS_FOLDER, PERSONAL_PLANS_FOLDER, PERSONAL_LOGS_FOLDER]:
            os.makedirs(folder, exist_ok=True)
        
        # Create personal log file if it doesn't exist
        if not os.path.exists(PERSONAL_LOG_FILE):
            self._initialize_personal_log()
    
    def _initialize_personal_log(self):
        """Initialize the personal log file."""
        content = f"""# Personal Task Log

## Purpose
Track all personal task routing and execution.

---

## Activity Log

*Generated automatically by Personal Task Handler*
"""
        with open(PERSONAL_LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _log_personal_activity(self, action: str, details: Dict[str, Any]) -> None:
        """
        Log personal task activity.
        
        Args:
            action: Action performed
            details: Action details
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            log_entry = f"[{timestamp}] {action} | {str(details)}\n"
            
            with open(PERSONAL_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            # Also log to system log
            self._log_to_system_log(action, details)
            
        except Exception as e:
            logger.error(f"Failed to log personal activity: {e}")
    
    def _log_to_system_log(self, action: str, details: Dict[str, Any]) -> None:
        """Log to the main system log."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            log_entry = f"[{timestamp}] PERSONAL_HANDLER | {action} | {str(details)}\n"
            
            with open(SYSTEM_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log to system log: {e}")
    
    def detect_task_type(self, task_content: str) -> str:
        """
        Detect whether a task is personal or business.
        
        Args:
            task_content: Task content to analyze
            
        Returns:
            'personal', 'business', or 'mixed'
        """
        return self.detector.detect_task_type(task_content)
    
    def route_personal_task(
        self,
        task_file: str,
        task_content: str,
        source_folder: str = "Inbox"
    ) -> Dict[str, Any]:
        """
        Route a personal task to the personal vault.
        
        Args:
            task_file: Original task filename
            task_content: Task content
            source_folder: Source folder (Inbox, Needs_Action, etc.)
            
        Returns:
            Dictionary with routing result
        """
        try:
            # Create personal task file
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            personal_task_filename = f"personal_task_{timestamp}.md"
            personal_task_path = os.path.join(PERSONAL_TASKS_FOLDER, personal_task_filename)
            
            # Modify task content for personal vault
            personal_content = self._adapt_task_for_personal_vault(
                task_content, task_file, source_folder
            )
            
            # Write personal task file
            with open(personal_task_path, 'w', encoding='utf-8') as f:
                f.write(personal_content)
            
            # Log the routing
            self._log_personal_activity(
                "route_personal_task",
                {
                    "original_file": task_file,
                    "personal_file": personal_task_filename,
                    "source_folder": source_folder,
                    "confidence": self.detector.get_confidence()
                }
            )
            
            logger.info(f"Personal task routed: {personal_task_filename}")
            
            return {
                "success": True,
                "personal_file": personal_task_filename,
                "personal_path": personal_task_path,
                "message": "Task routed to personal vault"
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to route personal task: {error_msg}")
            
            self._log_personal_activity(
                "route_personal_task_error",
                {
                    "original_file": task_file,
                    "error": error_msg
                }
            )
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "ROUTING_FAILED"
            }
    
    def _adapt_task_for_personal_vault(
        self,
        task_content: str,
        original_file: str,
        source_folder: str
    ) -> str:
        """
        Adapt task content for personal vault.
        
        Args:
            task_content: Original task content
            original_file: Original filename
            source_folder: Source folder
            
        Returns:
            Adapted task content
        """
        timestamp = datetime.now().isoformat()
        
        # Create personal task template
        personal_content = f"""---
Type: personal_task
Status: pending
Priority: medium
Created_at: {timestamp}
Original_file: {original_file}
Source_folder: {source_folder}
Domain: personal
---

# Personal Task: {original_file}

## Routing Information
- **Original File:** `{source_folder}/{original_file}`
- **Routed At:** {timestamp}
- **Detection Confidence:** {self.detector.get_confidence():.1%}

## Task Content

{task_content}

---

## Personal Notes
(Add any personal notes or context here)

---

## Completion Checklist

- [ ] Review task details
- [ ] Complete required actions
- [ ] Add personal notes
- [ ] Mark as complete

---

*Generated automatically by Personal Task Handler*
"""
        return personal_content
    
    def get_personal_tasks(self, status: str = "pending") -> List[Dict[str, Any]]:
        """
        Get list of personal tasks.
        
        Args:
            status: Filter by status (pending, completed, all)
            
        Returns:
            List of personal task dictionaries
        """
        tasks = []
        
        if not os.path.exists(PERSONAL_TASKS_FOLDER):
            return tasks
        
        try:
            for filename in os.listdir(PERSONAL_TASKS_FOLDER):
                if not filename.endswith('.md'):
                    continue
                
                filepath = os.path.join(PERSONAL_TASKS_FOLDER, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract task metadata
                task_data = self._parse_personal_task(content, filename, filepath)
                
                # Filter by status if requested
                if status != "all" and task_data.get('status') != status:
                    continue
                
                tasks.append(task_data)
            
            return sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get personal tasks: {e}")
            return []
    
    def _parse_personal_task(
        self,
        content: str,
        filename: str,
        filepath: str
    ) -> Dict[str, Any]:
        """
        Parse personal task content.
        
        Args:
            content: Task content
            filename: Filename
            filepath: File path
            
        Returns:
            Task data dictionary
        """
        task_data = {
            "filename": filename,
            "filepath": filepath,
            "status": "unknown",
            "created_at": "",
            "priority": "medium",
            "original_file": "",
            "source_folder": ""
        }
        
        # Extract YAML frontmatter
        if content.startswith('---'):
            lines = content.split('\n')
            in_frontmatter = False
            
            for line in lines:
                line = line.strip()
                
                if line == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                    else:
                        break
                    continue
                
                if in_frontmatter:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key in task_data:
                            task_data[key] = value
        
        return task_data
    
    def mark_personal_task_complete(self, filename: str) -> Dict[str, Any]:
        """
        Mark a personal task as complete.
        
        Args:
            filename: Task filename
            
        Returns:
            Dictionary with result
        """
        try:
            filepath = os.path.join(PERSONAL_TASKS_FOLDER, filename)
            
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": "Task file not found",
                    "error_code": "FILE_NOT_FOUND"
                }
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update status in frontmatter
            content = re.sub(
                r'Status:\s*\w+',
                'Status: completed',
                content,
                flags=re.IGNORECASE
            )
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._log_personal_activity(
                "mark_complete",
                {"filename": filename}
            )
            
            logger.info(f"Personal task marked complete: {filename}")
            
            return {
                "success": True,
                "message": "Task marked as completed"
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to mark task complete: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "error_code": "UPDATE_FAILED"
            }
    
    def get_personal_summary(self) -> Dict[str, Any]:
        """
        Get summary of personal tasks.
        
        Returns:
            Summary dictionary
        """
        all_tasks = self.get_personal_tasks(status="all")
        pending_tasks = self.get_personal_tasks(status="pending")
        completed_tasks = self.get_personal_tasks(status="completed")
        
        return {
            "total": len(all_tasks),
            "pending": len(pending_tasks),
            "completed": len(completed_tasks),
            "personal_vault_path": PERSONAL_VAULT
        }


# ============================================================
# Module Exports
# ============================================================

# Global instance for convenience
_personal_handler = None

def get_personal_handler() -> PersonalTaskHandler:
    """Get or create the personal task handler instance."""
    global _personal_handler
    if _personal_handler is None:
        _personal_handler = PersonalTaskHandler()
    return _personal_handler


def detect_task_type(task_content: str) -> str:
    """
    Detect whether a task is personal or business.
    
    Args:
        task_content: Task content to analyze
        
    Returns:
        'personal', 'business', or 'mixed'
    """
    handler = get_personal_handler()
    return handler.detect_task_type(task_content)


def route_personal_task(task_file: str, task_content: str, source_folder: str = "Inbox") -> Dict[str, Any]:
    """
    Route a personal task to the personal vault.
    
    Args:
        task_file: Original task filename
        task_content: Task content
        source_folder: Source folder
        
    Returns:
        Dictionary with routing result
    """
    handler = get_personal_handler()
    return handler.route_personal_task(task_file, task_content, source_folder)


def get_personal_tasks(status: str = "pending") -> List[Dict[str, Any]]:
    """
    Get list of personal tasks.
    
    Args:
        status: Filter by status
        
    Returns:
        List of personal task dictionaries
    """
    handler = get_personal_handler()
    return handler.get_personal_tasks(status)


def mark_personal_task_complete(filename: str) -> Dict[str, Any]:
    """
    Mark a personal task as complete.
    
    Args:
        filename: Task filename
        
    Returns:
        Dictionary with result
    """
    handler = get_personal_handler()
    return handler.mark_personal_task_complete(filename)


def get_personal_summary() -> Dict[str, Any]:
    """
    Get summary of personal tasks.
    
    Returns:
        Summary dictionary
    """
    handler = get_personal_handler()
    return handler.get_personal_summary()


__all__ = [
    'PersonalTaskHandler',
    'PersonalTaskDetector',
    'get_personal_handler',
    'detect_task_type',
    'route_personal_task',
    'get_personal_tasks',
    'mark_personal_task_complete',
    'get_personal_summary',
    'PERSONAL_VAULT',
    'PERSONAL_TASKS_FOLDER',
    'PERSONAL_PLANS_FOLDER',
    'PERSONAL_LOGS_FOLDER'
]
