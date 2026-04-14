"""Shared authentication utilities for MCP servers."""

import os
from pathlib import Path
from config import config


def get_google_credentials() -> dict:
    """Return Google OAuth credentials dict."""
    return {
        "client_id": config.google_client_id,
        "client_secret": config.google_client_secret,
        "redirect_uri": config.google_redirect_uri,
        "token_path": config.gmail_token_path,
        "credentials_path": config.gmail_credentials_path,
    }


def get_chrome_options() -> dict:
    """Return Chrome automation options."""
    return {
        "headless": config.chrome_headless,
        "user_data_dir": config.chrome_user_data_path,
    }


def require_env(key: str) -> str:
    """Assert an environment variable is set, raise if missing."""
    val = os.environ.get(key, "")
    if not val:
        raise EnvironmentError(f"Required environment variable {key} is not set")
    return val
