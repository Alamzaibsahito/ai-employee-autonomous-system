"""
Personal AI Employee - Central Configuration
Loads environment variables, validates settings, provides typed config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

# Load .env file
load_dotenv()

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent

# Vault paths
VAULT_ROOT = PROJECT_ROOT / "AI_Employee_Vault"
FOLDERS = {
    "inbox": VAULT_ROOT / "Inbox",
    "plans": VAULT_ROOT / "Plans",
    "needs_action": VAULT_ROOT / "Needs_Action",
    "pending_approval": VAULT_ROOT / "Pending_Approval",
    "approved": VAULT_ROOT / "Approved",
    "rejected": VAULT_ROOT / "Rejected",
    "done": VAULT_ROOT / "Done",
    "review_required": VAULT_ROOT / "Review_Required",
    "logs": VAULT_ROOT / "Logs",
    # Gold-level folders
    "briefings": VAULT_ROOT / "Briefings",
    "drafts": VAULT_ROOT / "Drafts",
    "content": VAULT_ROOT / "Content",
}

# Top-level folders
LOGS_DIR = PROJECT_ROOT / "Logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SKILLS_DIR = PROJECT_ROOT / "skills"
MCP_SERVERS_DIR = PROJECT_ROOT / "mcp_servers"
PIDS_DIR = PROJECT_ROOT / ".pids"


class Config(BaseModel):
    """Centralized configuration with validation."""

    # Google / Gmail
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://localhost:8080/callback", alias="GOOGLE_REDIRECT_URI")
    gmail_token_path: Path = Field(default=PROJECT_ROOT / "gmail_token.json", alias="GMAIL_TOKEN_PATH")
    gmail_credentials_path: Path = Field(default=PROJECT_ROOT / "credentials.json", alias="GMAIL_CREDENTIALS_PATH")

    # AI APIs
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # WhatsApp
    whatsapp_session_path: Path = Field(default=PROJECT_ROOT / "whatsapp_session", alias="WHATSAPP_SESSION_PATH")
    whatsapp_headless: bool = Field(default=False, alias="WHATSAPP_HEADLESS")

    # LinkedIn
    linkedin_session_path: Path = Field(default=PROJECT_ROOT / "linkedin_session", alias="LINKEDIN_SESSION_PATH")
    linkedin_headless: bool = Field(default=False, alias="LINKEDIN_HEADLESS")

    # Chrome
    chrome_user_data_path: str = Field(default=r"C:\chrome-automation-profile", alias="CHROME_USER_DATA_PATH")
    chrome_headless: bool = Field(default=False, alias="CHROME_HEADLESS")

    # Dashboard
    dashboard_port: int = Field(default=3000, alias="DASHBOARD_PORT")
    dashboard_host: str = Field(default="0.0.0.0", alias="DASHBOARD_HOST")

    # System
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    watchdog_restart_delay: int = Field(default=5, alias="WATCHDOG_RESTART_DELAY")
    ralph_loop_max_retries: int = Field(default=10, alias="RALPH_LOOP_MAX_RETRIES")
    approval_timeout_seconds: int = Field(default=3600, alias="APPROVAL_TIMEOUT_SECONDS")

    # Finance
    finance_api_key: str = Field(default="", alias="FINANCE_API_KEY")
    bank_api_url: str = Field(default="", alias="BANK_API_URL")

    # Gold-level: CEO Briefing
    business_goals_path: Path = Field(default=VAULT_ROOT / "Business_Goals.md", alias="BUSINESS_GOALS_PATH")
    ceo_briefing_day: str = Field(default="sunday", alias="CEO_BRIEFING_DAY")
    ceo_briefing_hour: int = Field(default=22, alias="CEO_BRIEFING_HOUR")  # 10 PM Sunday

    # Gold-level: Finance categories
    finance_subscription_threshold: float = Field(default=9.99, alias="FINANCE_SUBSCRIPTION_THRESHOLD")
    finance_anomaly_std_dev: float = Field(default=2.0, alias="FINANCE_ANOMALY_STD_DEV")
    finance_categories: str = Field(default="operational,marketing,software,salary,infrastructure,misc", alias="FINANCE_CATEGORIES")

    # Gold-level: LinkedIn automation
    linkedin_max_posts_per_day: int = Field(default=3, alias="LINKEDIN_MAX_POSTS_PER_DAY")
    linkedin_draft_folder: Path = Field(default=VAULT_ROOT / "Drafts", alias="LINKEDIN_DRAFT_FOLDER")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_env(cls) -> "Config":
        """Build config from environment variables."""
        return cls(**dict(os.environ))


# Singleton
config = Config.from_env()


def ensure_folders():
    """Create all required directories if they don't exist."""
    for folder in FOLDERS.values():
        folder.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PIDS_DIR.mkdir(parents=True, exist_ok=True)


def validate_config() -> list[str]:
    """Return list of missing critical configuration warnings."""
    warnings = []
    if not config.google_client_id:
        warnings.append("GOOGLE_CLIENT_ID not set — Gmail watcher will be disabled")
    if not config.anthropic_api_key and not config.openai_api_key:
        warnings.append("Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY set — AI reasoning disabled")
    if not config.gmail_credentials_path.exists():
        warnings.append(f"Gmail credentials not found at {config.gmail_credentials_path}")
    if not config.business_goals_path.exists():
        warnings.append(f"Business_Goals.md not found at {config.business_goals_path} — CEO Briefing will use defaults")
    return warnings
