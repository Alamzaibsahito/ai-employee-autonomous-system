"""
============================================================
Platinum Tier - Work-Zone Specialization
============================================================
Implements domain ownership for Cloud vs Local agents

Cloud Agent (Remote/VPS):
- Email triage
- Draft replies
- Draft social posts
- NEVER send directly

Local Agent (On-premise):
- Human approvals
- Payments
- Final send/post actions

Folder Structure:
- AI_Employee_Vault/Vault/ - Cloud workspace
- AI_Employee_Vault/Needs_Action/ - Tasks requiring action
- AI_Employee_Vault/Pending_Approval/ - Awaiting human approval
- AI_Employee_Vault/In_Progress/ - Currently being worked on
- AI_Employee_Vault/Updates/ - Status updates and alerts

Claim-by-Move Rule:
- To claim a task, move it to your domain folder
- Cloud moves to: AI_Employee_Vault/Vault/
- Local moves to: In_Progress/
- Prevents duplicate work
============================================================
"""

import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure logging
LOG_DIR = "Logs/central"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "work_zone.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# Folder Configuration
# ============================================================

class WorkZoneFolders:
    """Define work zone folder paths."""
    
    # Cloud Agent workspace
    CLOUD_VAULT = "AI_Employee_Vault/Vault"
    
    # Shared folders
    NEEDS_ACTION = "AI_Employee_Vault/Needs_Action"
    PENDING_APPROVAL = "AI_Employee_Vault/Pending_Approval"
    IN_PROGRESS = "AI_Employee_Vault/In_Progress"
    UPDATES = "AI_Employee_Vault/Updates"
    
    # Local Agent workspace
    LOCAL_APPROVED = "Approved"
    LOCAL_DONE = "Done"
    
    # Legacy folders (for backward compatibility)
    LEGACY_NEEDS_ACTION = "Needs_Action"
    LEGACY_PENDING_APPROVAL = "Pending_Approval"
    LEGACY_APPROVED = "Approved"
    LEGACY_DONE = "Done"
    
    def __init__(self):
        """Ensure all folders exist."""
        self.ensure_all_folders()
    
    def ensure_all_folders(self) -> None:
        """Create all work zone folders if they don't exist."""
        folders = [
            self.CLOUD_VAULT,
            self.NEEDS_ACTION,
            self.PENDING_APPROVAL,
            self.IN_PROGRESS,
            self.UPDATES,
            self.LOCAL_APPROVED,
            self.LOCAL_DONE,
            self.LEGACY_NEEDS_ACTION,
            self.LEGACY_PENDING_APPROVAL,
            self.LEGACY_APPROVED,
            self.LEGACY_DONE,
        ]
        
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
        
        logger.info("Work zone folders initialized")


# ============================================================
# Domain Agent Types
# ============================================================

class DomainType:
    """Domain agent type enumeration."""
    CLOUD = "cloud"
    LOCAL = "local"


class WorkZoneAgent:
    """
    Work-Zone Specialization Agent
    
    Implements claim-by-move rule for domain ownership.
    """
    
    def __init__(self, domain_type: str):
        self.domain_type = domain_type
        self.folders = WorkZoneFolders()
        self.claimed_tasks: List[str] = []
        
        logger.info(f"WorkZoneAgent initialized: {domain_type}")
    
    def claim_task(self, task_file: str, source_folder: str) -> Tuple[bool, str]:
        """
        Claim a task by moving it to domain workspace.
        
        Args:
            task_file: Task filename
            source_folder: Current location of task
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine destination based on domain
            if self.domain_type == DomainType.CLOUD:
                dest_folder = self.folders.CLOUD_VAULT
            else:
                dest_folder = self.folders.IN_PROGRESS
            
            # Build paths
            source_path = os.path.join(source_folder, task_file)
            dest_path = os.path.join(dest_folder, task_file)
            
            # Check if source exists
            if not os.path.exists(source_path):
                logger.warning(f"Task not found: {source_path}")
                return False, f"Task not found: {task_file}"
            
            # Check if already claimed
            if os.path.exists(dest_path):
                logger.warning(f"Task already claimed: {dest_path}")
                return False, f"Task already claimed"
            
            # Move task (claim by move)
            shutil.move(source_path, dest_path)
            
            self.claimed_tasks.append(task_file)
            
            logger.info(f"Task claimed: {task_file} -> {dest_folder}")
            
            # Log the claim
            self._log_claim(task_file, source_folder, dest_folder)
            
            return True, f"Task claimed: {task_file}"
            
        except Exception as e:
            logger.error(f"Failed to claim task: {e}")
            return False, str(e)
    
    def release_task(self, task_file: str, reason: str = "") -> Tuple[bool, str]:
        """
        Release a claimed task back to Needs_Action.
        
        Args:
            task_file: Task filename
            reason: Reason for release
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine source based on domain
            if self.domain_type == DomainType.CLOUD:
                source_folder = self.folders.CLOUD_VAULT
            else:
                source_folder = self.folders.IN_PROGRESS
            
            # Build paths
            source_path = os.path.join(source_folder, task_file)
            dest_path = os.path.join(self.folders.NEEDS_ACTION, task_file)
            
            # Check if source exists
            if not os.path.exists(source_path):
                logger.warning(f"Claimed task not found: {source_path}")
                return False, f"Task not found in workspace"
            
            # Move back to Needs_Action
            shutil.move(source_path, dest_path)
            
            if task_file in self.claimed_tasks:
                self.claimed_tasks.remove(task_file)
            
            # Write release reason
            self._write_release_note(task_file, reason)
            
            logger.info(f"Task released: {task_file} - {reason}")
            
            return True, f"Task released: {task_file}"
            
        except Exception as e:
            logger.error(f"Failed to release task: {e}")
            return False, str(e)
    
    def submit_for_approval(self, task_file: str, action_type: str) -> Tuple[bool, str]:
        """
        Submit completed work for human approval.
        
        Args:
            task_file: Task filename
            action_type: Type of action requiring approval
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Determine source based on domain
            if self.domain_type == DomainType.CLOUD:
                source_folder = self.folders.CLOUD_VAULT
            else:
                source_folder = self.folders.IN_PROGRESS
            
            # Build paths
            source_path = os.path.join(source_folder, task_file)
            
            # Check if source exists
            if not os.path.exists(source_path):
                logger.warning(f"Task not found: {source_path}")
                return False, f"Task not found in workspace"
            
            # Create approval request
            approval_id = f"approval_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            approval_file = os.path.join(self.folders.PENDING_APPROVAL, f"{approval_id}.md")
            
            # Read task content
            with open(source_path, 'r', encoding='utf-8') as f:
                task_content = f.read()
            
            # Create approval request
            approval_content = f"""---
Type: work_zone_approval
Domain: {self.domain_type}
Status: pending_approval
Created_at: {datetime.now().isoformat()}
Action_type: {action_type}
Source_task: {task_file}
---

# Approval Request: {action_type}

## Domain
{self.domain_type.upper()} Agent

## Requested Action
{action_type}

## Source Task
`{task_file}`

## Task Content
```
{task_content[:500]}...
```

---

## Human Decision Required

**To Approve:** Move this file to `Approved/` folder
**To Reject:** Delete this file or move to `Rejected/` folder

**Timestamp:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            with open(approval_file, 'w', encoding='utf-8') as f:
                f.write(approval_content)
            
            logger.info(f"Approval request created: {approval_id}")
            
            return True, f"Approval request created: {approval_id}"
            
        except Exception as e:
            logger.error(f"Failed to submit for approval: {e}")
            return False, str(e)
    
    def _log_claim(self, task_file: str, source: str, dest: str) -> None:
        """Log task claim to updates folder."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_file = os.path.join(
                self.folders.UPDATES,
                f"claim_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            update_content = f"""---
Type: task_claim
Timestamp: {datetime.now().isoformat()}
Domain: {self.domain_type}
---

# Task Claimed

- **Task:** `{task_file}`
- **From:** `{source}`
- **To:** `{dest}`
- **Domain:** {self.domain_type.upper()}
- **Time:** {timestamp}
"""
            
            with open(update_file, 'w', encoding='utf-8') as f:
                f.write(update_content)
                
        except Exception as e:
            logger.error(f"Failed to log claim: {e}")
    
    def _write_release_note(self, task_file: str, reason: str) -> None:
        """Write release note to updates folder."""
        try:
            update_file = os.path.join(
                self.folders.UPDATES,
                f"release_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            update_content = f"""---
Type: task_release
Timestamp: {datetime.now().isoformat()}
Domain: {self.domain_type}
---

# Task Released

- **Task:** `{task_file}`
- **Reason:** {reason}
- **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            with open(update_file, 'w', encoding='utf-8') as f:
                f.write(update_content)
                
        except Exception as e:
            logger.error(f"Failed to write release note: {e}")
    
    def get_workspace_status(self) -> Dict:
        """Get status of workspace."""
        if self.domain_type == DomainType.CLOUD:
            workspace = self.folders.CLOUD_VAULT
        else:
            workspace = self.folders.IN_PROGRESS
        
        try:
            tasks = os.listdir(workspace) if os.path.exists(workspace) else []
            return {
                "domain": self.domain_type,
                "workspace": workspace,
                "task_count": len(tasks),
                "tasks": tasks,
                "claimed_tasks": self.claimed_tasks
            }
        except Exception as e:
            logger.error(f"Failed to get workspace status: {e}")
            return {
                "domain": self.domain_type,
                "workspace": workspace,
                "task_count": 0,
                "tasks": [],
                "claimed_tasks": [],
                "error": str(e)
            }


# ============================================================
# Cloud Agent (Draft Mode Only)
# ============================================================

class CloudAgent(WorkZoneAgent):
    """
    Cloud Agent - Draft Mode Only
    
    Capabilities:
    - Email triage
    - Draft replies
    - Draft social posts
    - NEVER send directly
    
    All send actions require Local agent approval.
    """
    
    def __init__(self):
        super().__init__(DomainType.CLOUD)
        logger.info("CloudAgent initialized (Draft Mode)")
    
    def create_draft_email(self, task_file: str, content: str) -> Tuple[bool, str]:
        """Create a draft email (requires Local approval to send)."""
        try:
            draft_file = os.path.join(
                self.folders.CLOUD_VAULT,
                f"draft_email_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            draft_content = f"""---
Type: email_draft
Domain: cloud
Created_at: {datetime.now().isoformat()}
Status: draft
Source_task: {task_file}
---

# Draft Email

{content}

---

**Note:** This is a DRAFT. Requires Local agent approval to send.
"""
            
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(draft_content)
            
            logger.info(f"Draft email created: {draft_file}")
            
            return True, f"Draft email created"
            
        except Exception as e:
            logger.error(f"Failed to create draft email: {e}")
            return False, str(e)
    
    def create_draft_social_post(self, platform: str, content: str) -> Tuple[bool, str]:
        """Create a draft social post (requires Local approval to publish)."""
        try:
            draft_file = os.path.join(
                self.folders.CLOUD_VAULT,
                f"draft_{platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            draft_content = f"""---
Type: social_draft
Platform: {platform}
Domain: cloud
Created_at: {datetime.now().isoformat()}
Status: draft
---

# Draft {platform.title()} Post

{content}

---

**Note:** This is a DRAFT. Requires Local agent approval to publish.
"""
            
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(draft_content)
            
            logger.info(f"Draft {platform} post created: {draft_file}")
            
            return True, f"Draft {platform} post created"
            
        except Exception as e:
            logger.error(f"Failed to create draft social post: {e}")
            return False, str(e)


# ============================================================
# Local Agent (Final Actions)
# ============================================================

class LocalAgent(WorkZoneAgent):
    """
    Local Agent - Final Actions
    
    Capabilities:
    - Human approvals
    - Payments
    - Final send/post actions
    
    All actions require human approval workflow.
    """
    
    def __init__(self):
        super().__init__(DomainType.LOCAL)
        logger.info("LocalAgent initialized (Final Actions)")
    
    def process_approval(self, approval_file: str, approved: bool) -> Tuple[bool, str]:
        """Process an approval request."""
        try:
            source_path = os.path.join(self.folders.PENDING_APPROVAL, approval_file)
            
            if not os.path.exists(source_path):
                return False, f"Approval request not found: {approval_file}"
            
            if approved:
                dest_path = os.path.join(self.folders.LOCAL_APPROVED, approval_file)
                shutil.move(source_path, dest_path)
                logger.info(f"Approval granted: {approval_file}")
                return True, "Approval granted"
            else:
                os.remove(source_path)
                logger.info(f"Approval rejected: {approval_file}")
                return True, "Approval rejected"
                
        except Exception as e:
            logger.error(f"Failed to process approval: {e}")
            return False, str(e)
    
    def execute_payment(self, task_file: str, amount: float, recipient: str) -> Tuple[bool, str]:
        """Execute a payment (requires approval)."""
        try:
            # Create payment record
            payment_file = os.path.join(
                self.folders.LOCAL_APPROVED,
                f"payment_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            payment_content = f"""---
Type: payment_record
Timestamp: {datetime.now().isoformat()}
Amount: {amount}
Recipient: {recipient}
Source_task: {task_file}
---

# Payment Record

- **Amount:** ${amount:.2f}
- **Recipient:** {recipient}
- **Source Task:** {task_file}
- **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

**Status:** Recorded (requires external payment processor)
"""
            
            with open(payment_file, 'w', encoding='utf-8') as f:
                f.write(payment_content)
            
            logger.info(f"Payment recorded: {amount} to {recipient}")
            
            return True, f"Payment recorded: ${amount:.2f} to {recipient}"
            
        except Exception as e:
            logger.error(f"Failed to execute payment: {e}")
            return False, str(e)
    
    def finalize_send(self, draft_file: str) -> Tuple[bool, str]:
        """Finalize and send a draft (email or social)."""
        try:
            source_path = os.path.join(self.folders.CLOUD_VAULT, draft_file)
            
            if not os.path.exists(source_path):
                return False, f"Draft not found: {draft_file}"
            
            # Read draft
            with open(source_path, 'r', encoding='utf-8') as f:
                draft_content = f.read()
            
            # Create send record
            send_record = os.path.join(
                self.folders.LOCAL_DONE,
                f"sent_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
            )
            
            record_content = f"""---
Type: sent_item
Timestamp: {datetime.now().isoformat()}
Source_draft: {draft_file}
---

# Sent Item

**Draft:** {draft_file}

**Content:**
```
{draft_content}
```

---

**Status:** Sent by Local Agent
**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            with open(send_record, 'w', encoding='utf-8') as f:
                f.write(record_content)
            
            # Move draft to done
            dest_path = os.path.join(self.folders.LOCAL_DONE, draft_file)
            shutil.move(source_path, dest_path)
            
            logger.info(f"Draft finalized and sent: {draft_file}")
            
            return True, f"Draft finalized: {draft_file}"
            
        except Exception as e:
            logger.error(f"Failed to finalize send: {e}")
            return False, str(e)


# ============================================================
# Convenience Functions
# ============================================================

def get_cloud_agent() -> CloudAgent:
    """Get a Cloud Agent instance."""
    return CloudAgent()


def get_local_agent() -> LocalAgent:
    """Get a Local Agent instance."""
    return LocalAgent()


def initialize_work_zones() -> WorkZoneFolders:
    """Initialize work zone folders."""
    return WorkZoneFolders()


# ============================================================
# Main (Test/Demo)
# ============================================================

if __name__ == "__main__":
    logger.info("Work-Zone Specialization Module - Test Mode")
    
    # Initialize folders
    folders = initialize_work_zones()
    print("Work zone folders initialized")
    
    # Create agents
    cloud = get_cloud_agent()
    local = get_local_agent()
    
    print(f"\nCloud Agent Status: {cloud.get_workspace_status()}")
    print(f"Local Agent Status: {local.get_workspace_status()}")
    
    print("\nWork-Zone Specialization Module Ready")
