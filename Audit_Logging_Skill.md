---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Audit Logging Skill

## 1. Skill Name

**Audit_Logging**

## 2. Purpose

The Audit Logging skill provides a structured, immutable logging system for all AI Employee actions. Every action taken by the system is recorded in a standardized JSON format, ensuring complete traceability, accountability, and compliance. This enables post-incident analysis, compliance auditing, and system behavior understanding.

**Goal in simple terms:** Every action → Log it → Store it → Keep it safe → Enable audit

**Core principles:**
- **Completeness:** No action goes unlogged
- **Integrity:** Logs cannot be tampered with
- **Traceability:** Every action can be traced to source
- **Accountability:** Clear record of who/what did what
- **Security:** No sensitive data in logs

## 3. Log Structure Schema

### JSON Log Entry Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AI Employee Audit Log Entry",
  "type": "object",
  "required": [
    "log_id",
    "timestamp",
    "action_type",
    "actor",
    "target",
    "parameters",
    "approval_status",
    "result"
  ],
  "properties": {
    "log_id": {
      "type": "string",
      "description": "Unique identifier for this log entry",
      "format": "uuid"
    },
    "timestamp": {
      "type": "string",
      "description": "ISO 8601 timestamp of when action occurred",
      "format": "date-time"
    },
    "action_type": {
      "type": "string",
      "description": "Category of action performed",
      "enum": [
        "file_create",
        "file_read",
        "file_update",
        "file_delete",
        "file_move",
        "task_create",
        "task_update",
        "task_complete",
        "plan_generate",
        "approval_request",
        "approval_granted",
        "approval_denied",
        "email_send",
        "api_call",
        "scheduler_cycle",
        "error_occurred",
        "escalation",
        "system_start",
        "system_stop",
        "config_change"
      ]
    },
    "actor": {
      "type": "object",
      "description": "Entity that performed the action",
      "required": ["type", "name"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ai_agent", "human_user", "scheduler", "external_system"]
        },
        "name": {
          "type": "string",
          "description": "Identifier of the actor"
        },
        "session_id": {
          "type": "string",
          "description": "Session identifier for tracking related actions"
        }
      }
    },
    "target": {
      "type": "object",
      "description": "Resource or entity the action was performed on",
      "properties": {
        "type": {
          "type": "string",
          "description": "Type of target (file, task, folder, etc.)"
        },
        "path": {
          "type": "string",
          "description": "File system path or identifier"
        },
        "name": {
          "type": "string",
          "description": "Human-readable name"
        }
      }
    },
    "parameters": {
      "type": "object",
      "description": "Additional context about the action",
      "properties": {
        "description": {
          "type": "string",
          "description": "Human-readable description of what was done"
        },
        "details": {
          "type": "object",
          "description": "Action-specific details"
        }
      }
    },
    "approval_status": {
      "type": "object",
      "description": "Approval workflow status for sensitive actions",
      "properties": {
        "required": {
          "type": "boolean",
          "description": "Whether approval was required for this action"
        },
        "status": {
          "type": "string",
          "enum": ["not_required", "pending", "approved", "denied"],
          "description": "Current approval status"
        },
        "approved_by": {
          "type": "string",
          "description": "Identifier of who approved (if applicable)"
        },
        "approval_timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "When approval was granted"
        },
        "approval_file": {
          "type": "string",
          "description": "Path to approval request file"
        }
      }
    },
    "result": {
      "type": "object",
      "description": "Outcome of the action",
      "required": ["status"],
      "properties": {
        "status": {
          "type": "string",
          "enum": ["success", "failure", "partial", "skipped"]
        },
        "message": {
          "type": "string",
          "description": "Human-readable result message"
        },
        "error_code": {
          "type": "string",
          "description": "Error code if action failed"
        },
        "error_message": {
          "type": "string",
          "description": "Detailed error message if failed"
        },
        "duration_ms": {
          "type": "integer",
          "description": "Action duration in milliseconds"
        }
      }
    },
    "metadata": {
      "type": "object",
      "description": "Additional metadata for correlation and debugging",
      "properties": {
        "cycle_id": {
          "type": "string",
          "description": "Scheduler cycle identifier"
        },
        "correlation_id": {
          "type": "string",
          "description": "Links related log entries"
        },
        "source_file": {
          "type": "string",
          "description": "Source file that triggered the action"
        },
        "version": {
          "type": "string",
          "description": "Version of the skill/component"
        }
      }
    }
  }
}
```

### Visual Schema

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AUDIT LOG ENTRY STRUCTURE                      │
└─────────────────────────────────────────────────────────────────────┘

  {
    "log_id": "550e8400-e29b-41d4-a716-446655440000",
    │
    ├── "timestamp": "2026-02-17T14:30:00.000Z"
    │
    ├── "action_type": "task_create"
    │
    ├── "actor": {
    │     ├── "type": "ai_agent"
    │     ├── "name": "Vault_Watcher"
    │     └── "session_id": "session_20260217_143000"
    │   }
    │
    ├── "target": {
    │     ├── "type": "task_file"
    │     ├── "path": "Needs_Action/task_example_1708185600.md"
    │     └── "name": "task_example_1708185600.md"
    │   }
    │
    ├── "parameters": {
    │     ├── "description": "Created task from Inbox file"
    │     └── "details": {
    │         ├── "source_file": "Inbox/example.txt"
    │         └── "template_used": "plants/task_templete.md"
    │       }
    │   }
    │
    ├── "approval_status": {
    │     ├── "required": false
    │     └── "status": "not_required"
    │   }
    │
    ├── "result": {
    │     ├── "status": "success"
    │     ├── "message": "Task file created successfully"
    │     └── "duration_ms": 45
    │   }
    │
    └── "metadata": {
        ├── "cycle_id": "cycle_0042"
        ├── "correlation_id": "corr_abc123"
        ├── "source_file": "Inbox/example.txt"
        └── "version": "1.0.0"
      }
  }
```

## 4. Storage Rules

### File Naming Convention

```
Logs/YYYY-MM-DD.json
```

| Component | Format | Example |
|-----------|--------|---------|
| Year | YYYY | 2026 |
| Month | MM | 02 |
| Day | DD | 17 |

### Daily Log File Structure

```json
{
  "date": "2026-02-17",
  "version": "1.0",
  "created_at": "2026-02-17T00:00:00.000Z",
  "entries": [
    {
      "log_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-02-17T14:30:00.000Z",
      ...
    }
  ],
  "summary": {
    "total_entries": 0,
    "by_action_type": {},
    "by_actor": {},
    "by_result": {}
  }
}
```

### Storage Rules Table

| Rule | Description |
|------|-------------|
| **One file per day** | Each day gets its own JSON log file |
| **Append-only** | Entries are appended, never modified |
| **Atomic writes** | Use temp file + rename for integrity |
| **UTF-8 encoding** | All logs stored in UTF-8 |
| **Pretty print** | JSON formatted for readability |
| **Checksum file** | Optional .sha256 file for integrity verification |

### Storage Implementation

```python
import json
import os
from datetime import datetime
from pathlib import Path
import hashlib

class AuditLogger:
    def __init__(self, logs_dir="Logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        self.current_date = None
        self.current_file = None
        self.buffer = []
        self.buffer_size = 10  # Flush after N entries
    
    def _get_log_file_path(self, date=None):
        """Get path to log file for given date"""
        if date is None:
            date = datetime.now().date()
        return self.logs_dir / f"{date.isoformat()}.json"
    
    def _ensure_log_file(self):
        """Ensure current log file exists and is initialized"""
        today = datetime.now().date()
        
        if self.current_date != today:
            # Flush any pending entries from previous day
            self._flush()
            
            self.current_date = today
            self.current_file = self._get_log_file_path(today)
            
            # Initialize file if it doesn't exist
            if not self.current_file.exists():
                self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Create new daily log file with header"""
        header = {
            "date": self.current_date.isoformat(),
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "entries": [],
            "summary": {
                "total_entries": 0,
                "by_action_type": {},
                "by_actor": {},
                "by_result": {}
            }
        }
        
        # Write atomically using temp file
        temp_file = self.current_file.with_suffix('.json.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(header, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.current_file)
    
    def log(self, entry):
        """Log an audit entry"""
        # Add required fields if missing
        if 'log_id' not in entry:
            entry['log_id'] = self._generate_log_id()
        if 'timestamp' not in entry:
            entry['timestamp'] = datetime.now().isoformat()
        
        self.buffer.append(entry)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self._flush()
    
    def _flush(self):
        """Flush buffered entries to log file"""
        if not self.buffer:
            return
        
        self._ensure_log_file()
        
        # Read current file
        with open(self.current_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        # Append new entries
        log_data['entries'].extend(self.buffer)
        
        # Update summary
        self._update_summary(log_data, self.buffer)
        
        # Write atomically
        temp_file = self.current_file.with_suffix('.json.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.current_file)
        
        # Clear buffer
        self.buffer = []
    
    def _update_summary(self, log_data, entries):
        """Update summary statistics"""
        summary = log_data['summary']
        summary['total_entries'] = len(log_data['entries'])
        
        for entry in entries:
            # Count by action type
            action = entry.get('action_type', 'unknown')
            summary['by_action_type'][action] = summary['by_action_type'].get(action, 0) + 1
            
            # Count by actor
            actor = entry.get('actor', {}).get('name', 'unknown')
            summary['by_actor'][actor] = summary['by_actor'].get(actor, 0) + 1
            
            # Count by result
            result = entry.get('result', {}).get('status', 'unknown')
            summary['by_result'][result] = summary['by_result'].get(result, 0) + 1
```

## 5. Retention Policy

### Retention Schedule

| Log Age | Action |
|---------|--------|
| 0-7 days | Active (in primary Logs/ folder) |
| 8-30 days | Archived (compressed) |
| 31-90 days | Archived (compressed, cold storage) |
| 90+ days | Secure deletion |

### Retention Implementation

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LOG RETENTION LIFECYCLE                        │
└─────────────────────────────────────────────────────────────────────┘

  Day 0          Day 7          Day 30         Day 90
   │              │              │              │
   ▼              ▼              ▼              ▼
┌──────┐      ┌──────┐      ┌──────┐      ┌──────────┐
│ACTIVE│─────▶│ACTIVE│─────▶│ARCHIVE│────▶│  DELETE  │
│      │      │      │      │(compress)│    │(secure)  │
└──────┘      └──────┘      └──────┘      └──────────┘
   │              │              │
   │              │              │
   ▼              ▼              ▼
 Primary      Primary       Archive
 Logs/        Logs/         folder/
              (review       (cold
              window)       storage)
```

### Retention Configuration

```python
RETENTION_CONFIG = {
    "min_retention_days": 90,
    "archive_after_days": 30,
    "compress_after_days": 7,
    "delete_after_days": 365,  # Maximum retention
    "archive_folder": "Logs/Archive",
}
```

### Cleanup Script

```python
import gzip
import shutil
from datetime import datetime, timedelta

def manage_log_retention():
    """Manage log file retention and archiving"""
    logs_dir = Path("Logs")
    archive_dir = logs_dir / "Archive"
    archive_dir.mkdir(exist_ok=True)
    
    today = datetime.now().date()
    
    for log_file in logs_dir.glob("*.json"):
        # Extract date from filename
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d").date()
        except ValueError:
            continue  # Skip files that don't match naming pattern
        
        age_days = (today - file_date).days
        
        if age_days > RETENTION_CONFIG["delete_after_days"]:
            # Secure deletion
            secure_delete(log_file)
            print(f"Deleted old log: {log_file.name}")
        
        elif age_days > RETENTION_CONFIG["archive_after_days"]:
            # Move to archive
            archive_path = archive_dir / log_file.name
            if not archive_path.exists():
                shutil.move(str(log_file), str(archive_path))
                # Compress if old enough
                if age_days > RETENTION_CONFIG["compress_after_days"]:
                    compress_file(archive_path)
                print(f"Archived log: {log_file.name}")
        
        elif age_days > RETENTION_CONFIG["compress_after_days"]:
            # Compress in place
            compress_file(log_file)
            print(f"Compressed log: {log_file.name}")

def compress_file(file_path):
    """Compress a log file using gzip"""
    compressed_path = Path(str(file_path) + ".gz")
    
    with open(file_path, 'rb') as f_in:
        with gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # Remove original after successful compression
    file_path.unlink()

def secure_delete(file_path):
    """Securely delete a file by overwriting before removal"""
    file_size = file_path.stat().st_size
    
    # Overwrite with random data
    with open(file_path, 'wb') as f:
        f.write(os.urandom(file_size))
        f.flush()
        os.fsync(f.fileno())
    
    # Remove file
    file_path.unlink()
```

### Retention Log

```markdown
## Log Retention History

| Date | Action | Files Affected | Notes |
|------|--------|----------------|-------|
| 2026-02-17 | Archive | 2026-01-17.json | Moved to cold storage |
| 2026-02-17 | Delete | 2025-02-17.json.gz | Exceeded 365 day retention |
```

## 6. Security Rules

### Sensitive Data Handling

| Data Type | Action | Reason |
|-----------|--------|--------|
| **Passwords** | NEVER log | Credential exposure risk |
| **API Keys** | NEVER log | Security compromise risk |
| **Tokens** | NEVER log | Session hijacking risk |
| **Credit Cards** | NEVER log | PCI compliance |
| **Personal IDs** | Mask/Hash | Privacy compliance |
| **Email Content** | Summarize only | Privacy protection |

### Data Sanitization

```python
import re

class LogSanitizer:
    # Patterns to detect and remove sensitive data
    SENSITIVE_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?[^"\',\s]+', '[REDACTED]'),
        (r'api_key["\']?\s*[:=]\s*["\']?[^"\',\s]+', '[REDACTED]'),
        (r'token["\']?\s*[:=]\s*["\']?[^"\',\s]+', '[REDACTED]'),
        (r'secret["\']?\s*[:=]\s*["\']?[^"\',\s]+', '[REDACTED]'),
        (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CREDIT_CARD_REDACTED]'),
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),
    ]
    
    @classmethod
    def sanitize(cls, data):
        """Remove sensitive data from log entry"""
        if isinstance(data, dict):
            return {k: cls.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        elif isinstance(data, str):
            result = data
            for pattern, replacement in cls.SENSITIVE_PATTERNS:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            return result
        else:
            return data
    
    @classmethod
    def is_sensitive_key(cls, key):
        """Check if a key name suggests sensitive data"""
        sensitive_keys = [
            'password', 'passwd', 'pwd',
            'api_key', 'apikey', 'api-key',
            'secret', 'token', 'auth',
            'credential', 'private_key'
        ]
        return any(s in key.lower() for s in sensitive_keys)
```

### Security Rules Table

| Rule | Description | Enforcement |
|------|-------------|-------------|
| **No credentials in logs** | API keys, passwords, tokens never logged | Sanitization filter |
| **Immutable logs** | Log entries cannot be modified after write | Append-only file |
| **Access control** | Logs folder restricted permissions | File system permissions |
| **Integrity verification** | Optional checksums for audit files | SHA-256 hash |
| **No PII without consent** | Personal data requires explicit handling | Data minimization |
| **Encryption at rest** | Archived logs should be encrypted | GPG/encryption |

### Access Control

```bash
# Recommended folder permissions (Unix/Linux)
chmod 750 Logs/           # Owner rwx, group rx, others none
chmod 640 Logs/*.json     # Owner rw, group r, others none
chmod 640 Logs/Archive/*  # Archived logs same protection

# Windows equivalent (PowerShell)
icacls Logs /grant Users:(RX) Administrators:(F)
icacls Logs\*.json /grant Users:(R) Administrators:(F)
```

### Integrity Verification

```python
def generate_checksum(file_path):
    """Generate SHA-256 checksum for log file"""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def verify_checksum(file_path, expected_hash):
    """Verify log file integrity"""
    actual_hash = generate_checksum(file_path)
    return actual_hash == expected_hash

def create_checksum_file(log_file_path):
    """Create .sha256 checksum file"""
    checksum = generate_checksum(log_file_path)
    checksum_file = Path(str(log_file_path) + ".sha256")
    
    with open(checksum_file, 'w') as f:
        f.write(f"{checksum}  {log_file_path.name}\n")
```

## 7. Example Log Entry

### Complete Example: Task Creation

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2026-02-17T14:30:00.123Z",
  "action_type": "task_create",
  "actor": {
    "type": "ai_agent",
    "name": "Vault_Watcher",
    "session_id": "session_20260217_140000"
  },
  "target": {
    "type": "task_file",
    "path": "Needs_Action/task_client_brief_1708185600.md",
    "name": "task_client_brief_1708185600.md"
  },
  "parameters": {
    "description": "Created task from new Inbox file",
    "details": {
      "source_file": "Inbox/client_brief.txt",
      "template_used": "plants/task_templete.md",
      "task_type": "general_task",
      "priority": "medium"
    }
  },
  "approval_status": {
    "required": false,
    "status": "not_required"
  },
  "result": {
    "status": "success",
    "message": "Task file created successfully",
    "duration_ms": 45
  },
  "metadata": {
    "cycle_id": "cycle_0042",
    "correlation_id": "corr_watcher_001",
    "source_file": "Inbox/client_brief.txt",
    "version": "1.0.0"
  }
}
```

### Example: Approval Request

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440002",
  "timestamp": "2026-02-17T14:35:00.456Z",
  "action_type": "approval_request",
  "actor": {
    "type": "ai_agent",
    "name": "Task_Planner",
    "session_id": "session_20260217_140000"
  },
  "target": {
    "type": "approval_file",
    "path": "Pending_Approval/approval_email_client_1708185900.md",
    "name": "approval_email_client_1708185900.md"
  },
  "parameters": {
    "description": "Created approval request for external email",
    "details": {
      "action_type": "email_send",
      "recipient": "client@example.com",
      "subject": "Project Brief Summary",
      "risk_level": "medium",
      "source_task": "task_client_brief_1708185600.md"
    }
  },
  "approval_status": {
    "required": true,
    "status": "pending",
    "approval_file": "Pending_Approval/approval_email_client_1708185900.md"
  },
  "result": {
    "status": "success",
    "message": "Approval request created, awaiting human review",
    "duration_ms": 32
  },
  "metadata": {
    "cycle_id": "cycle_0042",
    "correlation_id": "corr_approval_001",
    "version": "1.0.0"
  }
}
```

### Example: Approval Granted & Action Executed

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440003",
  "timestamp": "2026-02-17T14:45:00.789Z",
  "action_type": "approval_granted",
  "actor": {
    "type": "human_user",
    "name": "john.doe",
    "session_id": "session_human_20260217_144500"
  },
  "target": {
    "type": "approval_file",
    "path": "Pending_Approval/approval_email_client_1708185900.md",
    "name": "approval_email_client_1708185900.md"
  },
  "parameters": {
    "description": "Human approved external email action",
    "details": {
      "approved_action": "email_send",
      "recipient": "client@example.com",
      "notes": "Approved - content reviewed"
    }
  },
  "approval_status": {
    "required": true,
    "status": "approved",
    "approved_by": "john.doe",
    "approval_timestamp": "2026-02-17T14:45:00.789Z"
  },
  "result": {
    "status": "success",
    "message": "Approval granted by human user",
    "duration_ms": 5
  },
  "metadata": {
    "correlation_id": "corr_approval_001",
    "version": "1.0.0"
  }
}
```

### Example: Error Occurred

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440004",
  "timestamp": "2026-02-17T15:00:00.000Z",
  "action_type": "error_occurred",
  "actor": {
    "type": "ai_agent",
    "name": "Vault_Watcher",
    "session_id": "session_20260217_140000"
  },
  "target": {
    "type": "file",
    "path": "Inbox/locked_document.docx",
    "name": "locked_document.docx"
  },
  "parameters": {
    "description": "Failed to read file - file locked by another process",
    "details": {
      "operation": "file_read",
      "error_category": "Transient",
      "retry_attempt": 2,
      "max_retries": 5
    }
  },
  "approval_status": {
    "required": false,
    "status": "not_required"
  },
  "result": {
    "status": "failure",
    "message": "File is locked by another process",
    "error_code": "FILE_LOCKED",
    "error_message": "The process cannot access the file because it is being used by another process.",
    "duration_ms": 1500
  },
  "metadata": {
    "cycle_id": "cycle_0043",
    "correlation_id": "corr_error_001",
    "version": "1.0.0"
  }
}
```

---

## Folder Structure

```
hackathon-0/
├── Logs/
│   ├── 2026-02-17.json       # Today's audit log
│   ├── 2026-02-16.json       # Previous day's audit log
│   ├── 2026-02-15.json.gz    # Compressed older log
│   ├── Archive/              # Archived logs (30+ days)
│   │   ├── 2026-01-15.json.gz
│   │   └── 2026-01-15.json.gz.sha256
│   ├── System_Log.md         # Human-readable system log
│   ├── watcher_errors.log    # Watcher-specific errors
│   └── retention_history.md  # Retention action history
└── ...
```

## Related Files

- `Vault_Watcher_Skill.md` — Creates tasks, generates audit logs
- `Task_Planner_Skill.md` — Generates plans, generates audit logs
- `Human_Approval_Skill.md` — Approval workflow, logged for audit
- `Scheduler_Daemon_Trigger_Skill.md` — Scheduler cycles logged
- `Error_Recovery_Skill.md` — Error events logged for analysis
- `Company_Handbook.md` — "Always log important actions"
