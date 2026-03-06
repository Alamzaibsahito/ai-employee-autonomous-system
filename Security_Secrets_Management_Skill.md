---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-17
---

# Security & Secrets Management Skill

## 1. Skill Name

**Security_Secrets**

## 2. Purpose

The Security & Secrets Management skill defines secure credential handling, environment isolation, and boundary enforcement for the Personal AI Employee system. It ensures that sensitive data (API keys, passwords, tokens) are never stored in the vault, uses environment variables for secrets, and enforces strict approval thresholds for sensitive actions.

**Goal in simple terms:** Secrets stay secret → Environments stay separate → Boundaries enforced → Safe by default

**Core principles:**
- **Zero trust:** Never trust, always verify
- **Least privilege:** Minimum permissions required
- **Defense in depth:** Multiple layers of protection
- **Local-first privacy:** Sensitive data stays local
- **Production-grade safety:** Safe defaults, explicit opt-in for risky actions

## 3. Credential Handling Rules

### ⚠️ CRITICAL: Never Store in Vault

| Secret Type | Examples | Storage Location |
|-------------|----------|------------------|
| **API Keys** | OpenAI, Anthropic, Stripe, Slack | Environment variable |
| **Passwords** | Email, database, service accounts | Environment variable |
| **Tokens** | OAuth tokens, session tokens | Memory only (runtime) |
| **Private Keys** | SSH keys, encryption keys | System keychain |
| **Database URLs** | Connection strings with credentials | Environment variable |
| **Webhook URLs** | Slack webhooks, Discord webhooks | Environment variable |

### ✅ Allowed in Vault (Non-Sensitive)

| Data Type | Examples | Notes |
|-----------|----------|-------|
| Task content | Task descriptions, checklists | No credentials |
| Plans | Action plans, strategies | No API keys |
| Logs | Audit logs, error logs | Sanitized only |
| Configuration | Non-sensitive settings | Feature flags, thresholds |

### Environment Variable Convention

```bash
# .env file (NEVER commit to version control)

# AI/LLM Services
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# Email Services
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASS=app-password-xxxxxxxxxxxxx

# Payment Services
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx

# Communication Services
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/xxx/xxx

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Application Settings
ENVIRONMENT=development
DEV_MODE=true
DRY_RUN=true

# Approval Thresholds
PAYMENT_APPROVAL_THRESHOLD=100.00
EMAIL_APPROVAL_REQUIRED=true
EXTERNAL_API_APPROVAL_REQUIRED=true
```

### .gitignore Configuration

```gitignore
# .gitignore - CRITICAL: Protect secrets

# Environment files
.env
.env.local
.env.*.local
.env.development
.env.production

# Runtime files
*.log
Logs/*.json
Logs/*.log
__pycache__/
*.pyc
*.pyo

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Temporary files
tmp/
temp/
*.tmp

# Secrets and keys (explicit backup protection)
*.key
*.pem
*.crt
secrets/
credentials/
```

### Loading Secrets Safely

```python
import os
from pathlib import Path
from dotenv import load_dotenv

class SecretsManager:
    """Securely load and manage secrets from environment variables"""
    
    REQUIRED_SECRETS = [
        'ANTHROPIC_API_KEY',  # Or other LLM provider
    ]
    
    OPTIONAL_SECRETS = [
        'SMTP_PASS',
        'STRIPE_SECRET_KEY',
        'SLACK_BOT_TOKEN',
    ]
    
    def __init__(self):
        self._load_env_file()
        self._validate_required_secrets()
    
    def _load_env_file(self):
        """Load .env file if it exists"""
        env_path = Path('.env')
        
        if env_path.exists():
            # Check .env file permissions (Unix/Linux)
            if os.name != 'nt':  # Not Windows
                mode = env_path.stat().st_mode
                if mode & 0o077:  # If group or others have any permissions
                    raise PermissionError(
                        f".env file has insecure permissions: {oct(mode)}. "
                        f"Should be 600 (owner read/write only)."
                    )
            
            load_dotenv(env_path)
        else:
            print("Warning: .env file not found. Using system environment variables.")
    
    def _validate_required_secrets(self):
        """Ensure all required secrets are present"""
        missing = []
        for secret in self.REQUIRED_SECRETS:
            if not os.getenv(secret):
                missing.append(secret)
        
        if missing:
            raise EnvironmentError(
                f"Missing required secrets: {', '.join(missing)}. "
                f"Please set these in your .env file or environment."
            )
    
    def get_secret(self, name, default=None):
        """Get a secret value by name"""
        value = os.getenv(name, default)
        
        if value is None:
            raise KeyError(f"Secret '{name}' not found")
        
        return value
    
    def get_api_key(self, service):
        """Get API key for a specific service"""
        key_name = f"{service.upper()}_API_KEY"
        return self.get_secret(key_name)
    
    def is_production(self):
        """Check if running in production environment"""
        return os.getenv('ENVIRONMENT', 'development') == 'production'
    
    def is_dev_mode(self):
        """Check if running in development mode"""
        return os.getenv('DEV_MODE', 'false').lower() == 'true'
    
    def is_dry_run(self):
        """Check if running in dry-run mode (no actual actions)"""
        return os.getenv('DRY_RUN', 'false').lower() == 'true'
```

## 4. Environment Isolation

### Environment Separation

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT ISOLATION                            │
└─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────┐         ┌─────────────────────┐
  │   DEVELOPMENT       │         │    PRODUCTION       │
  │   (Local/Safe)      │         │    (Live/Real)      │
  ├─────────────────────┤         ├─────────────────────┤
  │ .env.development    │         │ .env.production     │
  │ DEV_MODE=true       │         │ ENVIRONMENT=prod    │
  │ DRY_RUN=true        │         │ DRY_RUN=false       │
  │ Test API keys       │         │ Live API keys       │
  │ Test database       │         │ Production database │
  │ No real emails      │         │ Real emails sent    │
  │ No real payments    │         │ Real payments       │
  └─────────────────────┘         └─────────────────────┘
           │                               │
           │         ISOLATED              │
           └───────────────────────────────┘
                     (Never mix!)
```

### Environment Configuration

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `DEV_MODE` | `true` | `false` | `false` |
| `DRY_RUN` | `true` | `true` | `false` |
| `ENVIRONMENT` | `development` | `staging` | `production` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `APPROVAL_REQUIRED` | `false` (optional) | `true` | `true` |
| API Keys | Test/Sandbox | Test/Sandbox | Live |

### Environment Detection

```python
import os

class EnvironmentConfig:
    """Manage environment-specific configuration"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        
        # Validate environment configuration
        self._validate()
    
    def _validate(self):
        """Validate environment configuration for safety"""
        # Production must explicitly disable dry_run
        if self.environment == 'production' and self.dry_run:
            print("Warning: DRY_RUN enabled in production. This may be intentional for testing.")
        
        # Dev mode should not connect to production services
        if self.dev_mode and self.environment == 'production':
            raise ConfigurationError(
                "DEV_MODE cannot be enabled in production environment. "
                "This is a critical safety violation."
            )
    
    def get_api_base_url(self, service):
        """Get appropriate API base URL for environment"""
        urls = {
            'development': f"https://sandbox.{service}.com/api",
            'staging': f"https://staging.{service}.com/api",
            'production': f"https://api.{service}.com"
        }
        return urls.get(self.environment, urls['development'])
    
    def get_database_url(self):
        """Get appropriate database URL for environment"""
        if self.environment == 'production':
            return os.getenv('DATABASE_URL_PROD')
        elif self.environment == 'staging':
            return os.getenv('DATABASE_URL_STAGING')
        else:
            return os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    
    def should_require_approval(self, action_type):
        """Determine if approval is required based on environment"""
        # Production always requires approval for sensitive actions
        if self.environment == 'production':
            return action_type in ['payment', 'external_email', 'social_post']
        
        # Development may skip approval for testing
        if self.dev_mode:
            approval_override = os.getenv('APPROVAL_OVERRIDE', 'false')
            if approval_override.lower() == 'true':
                return False
        
        # Default: require approval
        return True
```

### Test vs Production Services

```python
# Service configuration by environment

SERVICE_CONFIG = {
    'email': {
        'development': {
            'host': 'smtp.mailtrap.io',  # Test email service
            'port': 587,
            'from_address': 'test@example.com'
        },
        'production': {
            'host': os.getenv('SMTP_HOST'),
            'port': int(os.getenv('SMTP_PORT', 587)),
            'from_address': os.getenv('SMTP_FROM')
        }
    },
    'payment': {
        'development': {
            'api_key': os.getenv('STRIPE_TEST_KEY'),  # Test key
            'webhook_secret': os.getenv('STRIPE_TEST_WEBHOOK')
        },
        'production': {
            'api_key': os.getenv('STRIPE_LIVE_KEY'),  # Live key
            'webhook_secret': os.getenv('STRIPE_LIVE_WEBHOOK')
        }
    }
}
```

## 5. Approval Threshold Rules

### Financial Approval Thresholds

| Amount Range | Approval Required | Approver | Notes |
|--------------|-------------------|----------|-------|
| $0 - $100 | Auto-approved (Dev only) | System | Dev mode only |
| $0 - $100 | Required | Any human | Production default |
| $100 - $1,000 | Required | Manager | Elevated threshold |
| $1,000+ | Required | Senior approval | High-value review |

### Email Approval Rules

| Recipient Type | Approval Required | Notes |
|----------------|-------------------|-------|
| Internal (same domain) | No | Auto-approved |
| External (new contact) | Yes | First-time contact |
| External (existing) | No | Previously approved |
| Bulk (>10 recipients) | Yes | Mass communication |
| Sensitive content | Yes | Financial, legal, HR |

### Threshold Configuration

```bash
# .env configuration for approval thresholds

# Payment thresholds (USD)
PAYMENT_AUTO_APPROVE_LIMIT=0          # 0 = no auto-approval
PAYMENT_SINGLE_APPROVAL_LIMIT=100     # Up to $100 single approval
PAYMENT_DUAL_APPROVAL_LIMIT=1000      # $100-$1000 requires dual approval
PAYMENT_SENIOR_APPROVAL_LIMIT=10000   # $1000+ requires senior approval

# Email settings
EMAIL_APPROVAL_REQUIRED=true          # Require approval for external emails
EMAIL_BULK_THRESHOLD=10               # Approval needed for >10 recipients
EMAIL_INTERNAL_DOMAIN=company.com     # Auto-approve internal emails

# API call settings
EXTERNAL_API_APPROVAL_REQUIRED=true   # Approval for external API mutations
READ_ONLY_API_APPROVAL=false          # No approval for GET requests

# File operation settings
FILE_DELETE_APPROVAL_REQUIRED=true    # Approval for file deletions
FILE_EXTERNAL_SHARE_APPROVAL=true     # Approval for external file sharing
```

### Threshold Enforcement

```python
class ApprovalThresholdEnforcer:
    """Enforce approval thresholds for sensitive actions"""
    
    def __init__(self):
        self.payment_limit = float(os.getenv('PAYMENT_SINGLE_APPROVAL_LIMIT', 100))
        self.email_approval = os.getenv('EMAIL_APPROVAL_REQUIRED', 'true').lower() == 'true'
        self.internal_domain = os.getenv('EMAIL_INTERNAL_DOMAIN', '')
    
    def check_payment_approval(self, amount, currency='USD'):
        """Check if payment requires approval and what level"""
        if amount <= 0:
            return {'required': False, 'level': 'none'}
        
        if amount <= self.payment_limit:
            # Check environment - dev mode may auto-approve small amounts
            if os.getenv('DEV_MODE', 'false').lower() == 'true':
                if os.getenv('PAYMENT_DEV_AUTO_APPROVE', 'false').lower() == 'true':
                    return {'required': False, 'level': 'auto_approved'}
            
            return {'required': True, 'level': 'single'}
        
        elif amount <= float(os.getenv('PAYMENT_DUAL_APPROVAL_LIMIT', 1000)):
            return {'required': True, 'level': 'dual'}
        
        elif amount <= float(os.getenv('PAYMENT_SENIOR_APPROVAL_LIMIT', 10000)):
            return {'required': True, 'level': 'senior'}
        
        else:
            return {'required': True, 'level': 'executive'}
    
    def check_email_approval(self, recipients, content_tags=None):
        """Check if email requires approval"""
        if not self.email_approval:
            return {'required': False, 'reason': 'disabled'}
        
        # Check for sensitive content tags
        sensitive_tags = ['financial', 'legal', 'hr', 'confidential']
        if content_tags and any(tag in content_tags for tag in sensitive_tags):
            return {'required': True, 'reason': 'sensitive_content'}
        
        # Check recipient count (bulk email)
        bulk_threshold = int(os.getenv('EMAIL_BULK_THRESHOLD', 10))
        if len(recipients) > bulk_threshold:
            return {'required': True, 'reason': 'bulk_email'}
        
        # Check if all recipients are internal
        if self.internal_domain:
            all_internal = all(
                self.internal_domain in recipient 
                for recipient in recipients
            )
            if all_internal:
                return {'required': False, 'reason': 'internal_only'}
        
        # Check if any recipient is new (first-time contact)
        # This would require checking against a contact database
        has_new_contact = self._check_new_contacts(recipients)
        if has_new_contact:
            return {'required': True, 'reason': 'new_external_contact'}
        
        return {'required': False, 'reason': 'existing_external'}
    
    def _check_new_contacts(self, recipients):
        """Check if any recipient is a new contact"""
        # Implementation would check against stored contacts
        # For now, assume all external are new (safest default)
        return True
```

## 6. Security Boundaries

### Boundary Enforcement Matrix

| Action | Dev Mode | Dry Run | Production |
|--------|----------|---------|------------|
| Read files | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| Create tasks | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| Generate plans | ✅ Allowed | ✅ Allowed | ✅ Allowed |
| Send internal email | ✅ Allowed | ❌ Blocked | ✅ + Approval |
| Send external email | ❌ Blocked | ❌ Blocked | ✅ + Approval |
| Process payment | ❌ Blocked | ❌ Blocked | ✅ + Approval |
| Delete files | ⚠️ Warning | ❌ Blocked | ✅ + Approval |
| External API write | ❌ Blocked | ❌ Blocked | ✅ + Approval |
| External API read | ✅ Allowed | ✅ Mocked | ✅ Allowed |

### Safety Guardrails

```python
class SecurityGuardrails:
    """Enforce security boundaries for all actions"""
    
    # Actions that are NEVER allowed without explicit human approval
    FORBIDDEN_WITHOUT_APPROVAL = [
        'payment_process',
        'external_email_send',
        'file_delete',
        'file_external_share',
        'database_write',
        'api_mutation',
        'social_media_post',
        'credential_access'
    ]
    
    # Actions that are NEVER allowed in any mode
    ABSOLUTELY_FORBIDDEN = [
        'secret_exfiltration',
        'credential_logging',
        'env_file_modification',
        'gitignore_bypass'
    ]
    
    def __init__(self):
        self.dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        self.environment = os.getenv('ENVIRONMENT', 'development')
    
    def check_action_allowed(self, action_type, context=None):
        """Check if an action is allowed given current security context"""
        
        # Check absolutely forbidden actions
        if action_type in self.ABSOLUTELY_FORBIDDEN:
            raise SecurityViolation(
                f"Action '{action_type}' is absolutely forbidden. "
                "This is a critical security boundary."
            )
        
        # Check forbidden without approval
        if action_type in self.FORBIDDEN_WITHOUT_APPROVAL:
            if not context or not context.get('approval_granted'):
                raise ApprovalRequired(
                    f"Action '{action_type}' requires human approval. "
                    "Please create an approval request."
                )
        
        # Environment-specific checks
        if self.environment == 'production':
            # Production has strictest rules
            if self.dry_run and action_type in ['payment_process', 'external_email_send']:
                raise DryRunBlocked(
                    f"Action '{action_type}' blocked in dry-run mode. "
                    "Set DRY_RUN=false to enable (production only)."
                )
        
        elif self.dev_mode:
            # Dev mode blocks certain dangerous actions entirely
            dev_blocked = ['payment_process', 'external_email_send', 'file_delete']
            if action_type in dev_blocked:
                raise DevModeBlocked(
                    f"Action '{action_type}' is blocked in development mode. "
                    "Switch to production environment to enable."
                )
        
        return {'allowed': True, 'action': action_type}
    
    def validate_no_secrets_in_content(self, content):
        """Scan content for potential secrets"""
        secret_patterns = [
            r'sk-[a-zA-Z0-9]{20,}',  # API keys
            r'password\s*[:=]\s*\S+',  # Passwords
            r'api_key\s*[:=]\s*\S+',  # API keys
            r'token\s*[:=]\s*\S+',  # Tokens
        ]
        
        import re
        found_secrets = []
        
        for pattern in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            found_secrets.extend(matches)
        
        if found_secrets:
            raise SecretDetected(
                f"Potential secrets detected in content: {found_secrets}. "
                "Secrets must never be stored in vault files."
            )
        
        return {'valid': True}
```

### Security Violation Handling

```python
class SecurityViolation(Exception):
    """Base exception for security violations"""
    pass

class ApprovalRequired(SecurityViolation):
    """Action requires human approval"""
    pass

class DevModeBlocked(SecurityViolation):
    """Action blocked in development mode"""
    pass

class DryRunBlocked(SecurityViolation):
    """Action blocked in dry-run mode"""
    pass

class SecretDetected(SecurityViolation):
    """Secret detected in content"""
    pass

def handle_security_violation(violation, context=None):
    """Handle security violations with appropriate logging and escalation"""
    import json
    from datetime import datetime
    
    # Log the violation (without sensitive details)
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': 'security_violation',
        'violation_type': type(violation).__name__,
        'message': str(violation),
        'environment': os.getenv('ENVIRONMENT', 'unknown'),
        'dev_mode': os.getenv('DEV_MODE', 'false'),
        'dry_run': os.getenv('DRY_RUN', 'false'),
    }
    
    # Write to security log
    with open('Logs/security_violations.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # For critical violations, create escalation file
    if type(violation) in [SecretDetected, SecurityViolation]:
        create_security_escalation(log_entry)
    
    # Re-raise for caller to handle
    raise violation
```

## 7. Example Configuration

### Complete .env Example

```bash
# ============================================================
# AI Employee System - Environment Configuration
# ============================================================
# WARNING: This file contains sensitive credentials
# - NEVER commit this file to version control
# - Use 600 permissions (owner read/write only)
# - Rotate secrets regularly
# ============================================================

# ------------------------------------------------------------
# Environment Settings
# ------------------------------------------------------------
ENVIRONMENT=development
DEV_MODE=true
DRY_RUN=true
LOG_LEVEL=DEBUG

# ------------------------------------------------------------
# AI/LLM Services
# ------------------------------------------------------------
ANTHROPIC_API_KEY=sk-ant-test-xxxxxxxxxxxxxxxxxxxxx
# For production, use: ANTHROPIC_API_KEY=sk-ant-live-xxxxx

# ------------------------------------------------------------
# Email Services (Development - Mailtrap)
# ------------------------------------------------------------
SMTP_HOST=smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=mailtrap_user_xxxxx
SMTP_PASS=mailtrap_pass_xxxxx
SMTP_FROM=test@example.com

# Production Email (Uncomment for production)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=user@company.com
# SMTP_PASS=app-password-xxxxx
# SMTP_FROM=noreply@company.com

# ------------------------------------------------------------
# Payment Services (Stripe Test)
# ------------------------------------------------------------
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxxxxxxxxxxxxxxxxxxxx

# Production Payment (Uncomment for production)
# STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
# STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
# STRIPE_WEBHOOK_SECRET=whsec_live_xxxxxxxxxxxxxxxxxxxxx

# ------------------------------------------------------------
# Communication Services
# ------------------------------------------------------------
SLACK_BOT_TOKEN=xoxb-test-xxxxxxxxxxxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxx

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
DATABASE_URL=sqlite:///dev.db
# Production: DATABASE_URL=postgresql://user:pass@host:5432/db

# ------------------------------------------------------------
# Approval Thresholds
# ------------------------------------------------------------
PAYMENT_AUTO_APPROVE_LIMIT=0
PAYMENT_SINGLE_APPROVAL_LIMIT=100
PAYMENT_DUAL_APPROVAL_LIMIT=1000
PAYMENT_SENIOR_APPROVAL_LIMIT=10000

EMAIL_APPROVAL_REQUIRED=true
EMAIL_BULK_THRESHOLD=10
EMAIL_INTERNAL_DOMAIN=company.com

EXTERNAL_API_APPROVAL_REQUIRED=true
FILE_DELETE_APPROVAL_REQUIRED=true

# ------------------------------------------------------------
# Development Overrides (Only used when DEV_MODE=true)
# ------------------------------------------------------------
APPROVAL_OVERRIDE=false
PAYMENT_DEV_AUTO_APPROVE=false
```

### Production .env Example

```bash
# ============================================================
# AI Employee System - PRODUCTION Configuration
# ============================================================
# CRITICAL: This file contains LIVE credentials
# - Store in secure secrets manager in production
# - Never commit to version control
# - Audit access regularly
# ============================================================

# ------------------------------------------------------------
# Environment Settings (PRODUCTION)
# ------------------------------------------------------------
ENVIRONMENT=production
DEV_MODE=false
DRY_RUN=false
LOG_LEVEL=WARNING

# ------------------------------------------------------------
# AI/LLM Services (LIVE)
# ------------------------------------------------------------
ANTHROPIC_API_KEY=sk-ant-live-xxxxxxxxxxxxxxxxxxxxx

# ------------------------------------------------------------
# Email Services (LIVE)
# ------------------------------------------------------------
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=noreply@company.com
SMTP_PASS=<secure-password>
SMTP_FROM=noreply@company.com

# ------------------------------------------------------------
# Payment Services (LIVE)
# ------------------------------------------------------------
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_live_xxxxxxxxxxxxxxxxxxxxx

# ------------------------------------------------------------
# Database (PRODUCTION)
# ------------------------------------------------------------
DATABASE_URL=postgresql://user:<secure-pass>@prod-db:5432/employee_db

# ------------------------------------------------------------
# Security Settings (PRODUCTION - Strict)
# ------------------------------------------------------------
PAYMENT_AUTO_APPROVE_LIMIT=0
PAYMENT_SINGLE_APPROVAL_LIMIT=100
EMAIL_APPROVAL_REQUIRED=true
EXTERNAL_API_APPROVAL_REQUIRED=true
FILE_DELETE_APPROVAL_REQUIRED=true
```

### Setup Script

```bash
#!/bin/bash
# setup_env.sh - Initialize secure environment

echo "Setting up secure environment..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your credentials."
else
    echo ".env file already exists."
fi

# Set secure permissions (Unix/Linux/Mac)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    chmod 600 .env
    echo "Set .env permissions to 600 (owner read/write only)."
fi

# Check for .gitignore
if [ ! -f .gitignore ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Environment files
.env
.env.local
.env.*.local

# Logs
*.log
Logs/*.json
Logs/*.log

# Python
__pycache__/
*.pyc
*.pyo
EOF
    echo "Created .gitignore with security exclusions."
else
    # Verify .env is in .gitignore
    if ! grep -q "^\.env$" .gitignore; then
        echo "WARNING: .env is not in .gitignore! Adding it now..."
        echo ".env" >> .gitignore
    fi
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Never commit .env to version control"
echo "3. Run: source .env (or use python-dotenv)"
```

---

## Folder Structure

```
hackathon-0/
├── .env                    # Secrets (NEVER commit)
├── .env.example            # Template (safe to commit)
├── .gitignore              # Excludes .env from git
├── Logs/
│   ├── security_violations.jsonl  # Security event log
│   └── ...
├── bronze/
│   ├── Security_Secrets_Management_Skill.md  # This skill
│   ├── Human_Approval_Skill.md   # Approval workflow
│   └── ...
└── scripts/
    └── setup_env.sh        # Environment setup script
```

## Related Files

- `Human_Approval_Skill.md` — Approval workflow for sensitive actions
- `Audit_Logging_Skill.md` — Security events logged for audit
- `Error_Recovery_Skill.md` — Security violation handling
- `Company_Handbook.md` — "Never take destructive actions without confirmation"
