"""
WhatsApp Watcher — Monitors WhatsApp Web for new messages and creates tasks.
Uses Playwright to interact with WhatsApp Web session.
Inherits from BaseWatcher for common task management functionality.
"""

import time
import json
from pathlib import Path
from datetime import datetime, timezone

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log
from scripts.base_watcher import BaseWatcher


class WhatsAppWatcher(BaseWatcher):
    """WhatsApp Web watcher that monitors for new messages."""

    def __init__(self, poll_interval: int = 10):
        super().__init__(name="whatsapp", poll_interval=poll_interval)
        self.state_file = FOLDERS["logs"] / "whatsapp_state.json"

        # Persistent browser instances (reused across polling cycles)
        self._playwright = None
        self._context = None
        self._page = None

    # ─── Browser Lifecycle ─────────────────────────────────────────────

    # Fallback selectors for WhatsApp Web UI (tried in order)
    _WA_SELECTORS = [
        '[data-testid="chat-list"]',
        '[data-testid="chat-list-mode"]',
        '[data-testid="pane-body"]',
        '[data-testid="search-input"]',
        '#pane-side',
        'div[role="grid"]',
    ]

    def _is_page_healthy(self, retries: int = 2) -> bool:
        """
        Check if the WhatsApp Web page is alive and responsive.
        Tries multiple selectors with retries before declaring page dead.
        """
        if not self._page or not self._context or not self._playwright:
            return False

        try:
            if self._page.is_closed():
                logger.debug("[WhatsApp] Page is closed")
                return False
        except Exception:
            return False

        # Try a few times before declaring the page dead
        for attempt in range(1, retries + 1):
            try:
                # Try each selector — any match means page is alive
                for selector in self._WA_SELECTORS:
                    try:
                        self._page.wait_for_selector(
                            selector,
                            state="attached",
                            timeout=3000,
                        )
                        logger.debug(f"[WhatsApp] Health OK via selector: {selector}")
                        return True
                    except Exception:
                        continue  # Try next selector

                logger.debug(f"[WhatsApp] Health check attempt {attempt}/{retries}: no selectors matched")
                if attempt < retries:
                    try:
                        self._page.wait_for_timeout(1000)
                    except Exception:
                        return False
            except Exception:
                if attempt == retries:
                    return False

        return False

    def _detect_login_state(self) -> str:
        """
        Detect whether WhatsApp Web is logged in or showing QR code.
        Returns: 'logged_in', 'qr_code', or 'unknown'
        """
        try:
            # QR code page indicators
            qr_canvas = self._page.query_selector('canvas[data-testid="qr-code"]')
            if qr_canvas:
                return "qr_code"

            # Alternative QR selector
            qr_img = self._page.query_selector('[data-testid="qr-code"]')
            if qr_img:
                return "qr_code"

            # Also check for the QR wrapper
            qr_wrapper = self._page.query_selector('#app div[data-testid="chat-list"]')
            if not qr_wrapper:
                # If no chat-list AND no QR, might still be loading — check for login button
                login_btn = self._page.query_selector('[data-testid="landing-button-link"]')
                if login_btn:
                    return "qr_code"

            # If we can find chat-related elements, we're logged in
            for selector in self._WA_SELECTORS:
                if self._page.query_selector(selector):
                    return "logged_in"

            return "unknown"

        except Exception as e:
            logger.debug(f"[WhatsApp] Login detection error: {e}")
            return "unknown"

    def _wait_for_whatsapp_ready(self, timeout: int = 60000) -> bool:
        """
        Wait for WhatsApp Web to be fully loaded and logged in.
        If QR code is detected, waits for user to scan (non-headless mode required).
        Returns True when chat list is visible, False on timeout.
        """
        logger.info("[WhatsApp] Waiting for WhatsApp Web to load...")

        # Phase 1: Wait for DOM to show either QR or chat interface
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=30000)
            logger.info("[WhatsApp] DOM content loaded")
        except Exception:
            logger.warning("[WhatsApp] DOM load timeout — page may be slow")

        # Phase 2: Detect login state
        login_state = self._detect_login_state()

        if login_state == "qr_code":
            logger.warning(
                "[WhatsApp] ⚠️  QR CODE DETECTED — Please scan QR code with your phone"
            )
            logger.info(
                "[WhatsApp] Browser will stay open. Waiting up to 120 seconds for login..."
            )

            # Poll for login completion (user scans QR)
            for i in range(24):  # 24 * 5s = 120s max wait
                try:
                    self._page.wait_for_timeout(5000)
                    state = self._detect_login_state()
                    if state == "logged_in":
                        logger.info("[WhatsApp] ✅ Login detected — QR scan successful!")
                        break
                    elif state == "qr_code":
                        if i % 6 == 0:  # Every 30s
                            logger.info("[WhatsApp] Still waiting for QR scan...")
                    else:
                        logger.debug(f"[WhatsApp] Login state: {state}")
                except Exception:
                    pass
            else:
                logger.error("[WhatsApp] QR scan timeout — no login detected after 120s")
                return False

        # Phase 3: Wait for chat list using fallback selectors
        logger.info("[WhatsApp] Waiting for chat interface to load...")
        for selector in self._WA_SELECTORS:
            try:
                self._page.wait_for_selector(
                    selector,
                    state="attached",
                    timeout=10000,
                )
                logger.info(f"[WhatsApp] ✅ WhatsApp ready (detected via: {selector})")
                return True
            except Exception:
                continue  # Try next selector

        logger.error("[WhatsApp] Chat interface did not load within timeout")
        return False

    def _ensure_browser(self):
        """Launch browser once, reuse across cycles. Safe against crashes."""
        from playwright.sync_api import sync_playwright

        # If everything is healthy, reuse existing instances
        if self._is_page_healthy():
            logger.debug("[WhatsApp] Reusing existing browser session")
            return

        # Only restart if health check genuinely failed
        if self._page or self._context or self._playwright:
            logger.warning("[WhatsApp] Browser health check failed after retries, restarting...")
            self._close_browser()

        logger.info("[WhatsApp] Launching Playwright browser (first time or recovery)...")

        # Force non-headless if no session exists (need QR scan)
        force_headless = config.whatsapp_headless
        if not config.whatsapp_session_path.exists():
            logger.info("[WhatsApp] No existing session — forcing non-headless mode for QR scan")
            force_headless = False

        try:
            self._playwright = sync_playwright().start()

            logger.info(f"[WhatsApp] Launching browser (headless={force_headless})...")
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(config.whatsapp_session_path),
                headless=force_headless,
                viewport={"width": 1280, "height": 720},
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

            logger.info("[WhatsApp] Navigating to WhatsApp Web...")
            self._page.goto(
                "https://web.whatsapp.com",
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Wait for WhatsApp to be fully loaded (handles QR scan flow)
            ready = self._wait_for_whatsapp_ready(timeout=60000)
            if not ready:
                logger.error("[WhatsApp] WhatsApp Web did not load successfully")
                self._close_browser()
                return  # Don't raise — let next cycle retry gracefully

            logger.info("[WhatsApp] Browser session ready")

        except Exception as e:
            logger.error(f"[WhatsApp] Browser launch failed: {e}")
            self._close_browser()

    def _close_browser(self):
        """Safely close browser resources."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._playwright = None

    def stop(self):
        """Stop the watcher and close the browser."""
        self._running = False
        self._close_browser()
        logger.info(f"{self.name.capitalize()} Watcher stopping...")
        audit_log(action=f"{self.name}_watcher_stopped")

    # ─── Event Checking (No Browser Launch) ────────────────────────────

    def check_for_events(self) -> int:
        """
        Check WhatsApp for new messages using Playwright.
        Returns number of new tasks created.
        Reuses persistent browser session — no launch/close per cycle.
        """
        ensure_folders()
        state = self.load_state(default={"last_messages": {}, "last_check": None})
        tasks_created = 0

        try:
            # Ensure browser is running (launches once, reuses session)
            self._ensure_browser()

            if not self._page:
                logger.warning("[WhatsApp] Browser not available, skipping this cycle")
                return 0

            logger.info("[WhatsApp] Scanning for unread chats...")

            try:
                # Get chat list with unread messages
                unread_chats = self._page.evaluate("""() => {
                    const items = document.querySelectorAll('div[data-testid="cell-frame-container"]');
                    return Array.from(items).map(item => {
                        const badge = item.querySelector('span[data-testid="unread"]');
                        return {
                            name: item.querySelector('span[title]')?.getAttribute('title') || '',
                            has_unread: badge !== null,
                            last_msg: item.querySelector('span[data-testid="cell-frame-title"]')?.textContent?.trim() || ''
                        };
                    }).filter(c => c.has_unread);
                }""")

                logger.info(f"[WhatsApp] Found {len(unread_chats)} unread chat(s)")

                for chat in unread_chats:
                    contact = chat["name"]
                    last_msg_key = f"{contact}_last_msg"
                    prev_msg = state["last_messages"].get(last_msg_key, "")

                    is_new = chat["last_msg"] != prev_msg
                    logger.debug(f"[WhatsApp] Contact '{contact}': new_message={is_new}")

                    if is_new:
                        self._create_whatsapp_task(contact, chat["last_msg"])
                        state["last_messages"][last_msg_key] = chat["last_msg"]
                        tasks_created += 1
                        logger.info(
                            f"WhatsApp Watcher: New message from {contact}"
                        )
                        self.log_event(
                            action="new_message",
                            details={"contact": contact},
                        )

            except Exception as e:
                # Page crashed or stale — browser will restart on next cycle
                logger.warning(f"[WhatsApp] Page evaluation failed: {e} — will retry next cycle")
                self._close_browser()

            # Prune old state
            self.prune_state(state, "last_messages", max_items=100)

            # Update last check timestamp
            state = self.update_last_check(state)
            self.save_state(state)

            logger.info(f"[WhatsApp] Check cycle complete — {tasks_created} new task(s) created")

        except Exception as e:
            logger.error(f"WhatsApp Watcher error: {e}")
            self.log_event(action="watcher_error", details={"error": str(e)})

        return tasks_created

    def _create_whatsapp_task(self, contact: str, message_preview: str):
        """Create a task file for a new WhatsApp message using BaseWatcher helpers."""
        task_id = self.generate_task_id("WA", f"{contact}_{message_preview}")
        timestamp = datetime.now(timezone.utc).isoformat()

        metadata = {
            "contact": contact,
            "priority": "normal",
        }

        content = f"""# Task: WhatsApp Message from {contact}

**Source:** WhatsApp Watcher
**Contact:** {contact}
**Time:** {timestamp}

## Message Preview
{message_preview}

## Action Required
> [!TODO] Review message and respond if needed

## Notes
- Auto-created by WhatsApp Watcher
- Open WhatsApp Web to see full conversation
"""
        task_path = self.create_task_file(
            task_id=task_id,
            metadata=metadata,
            content=content,
            destination="inbox",
        )

        logger.info(f"WhatsApp Watcher: Created task {task_id} for {contact}")


# ─── Backward Compatibility ────────────────────────────────────────────

# Module-level singleton reused across all backward-compat function calls
_watcher_instance: WhatsAppWatcher | None = None


def _get_watcher() -> WhatsAppWatcher:
    """Get or create the singleton WhatsAppWatcher instance."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = WhatsAppWatcher()
    return _watcher_instance


def load_state() -> dict:
    """Load WhatsApp watcher state (backward compatibility)."""
    return _get_watcher().load_state(default={"last_messages": {}, "last_check": None})


def save_state(state: dict):
    """Save WhatsApp watcher state (backward compatibility)."""
    _get_watcher().save_state(state)


def create_whatsapp_task(contact: str, message_preview: str, timestamp: str) -> str:
    """Create a task file for a new WhatsApp message (backward compatibility)."""
    watcher = _get_watcher()
    task_id = watcher.generate_task_id("WA", f"{contact}_{message_preview}")
    metadata = {"contact": contact, "priority": "normal"}
    content = f"""# Task: WhatsApp Message from {contact}

**Source:** WhatsApp Watcher
**Contact:** {contact}
**Time:** {timestamp}

## Message Preview
{message_preview}

## Action Required
> [!TODO] Review message and respond if needed

## Notes
- Auto-created by WhatsApp Watcher
- Open WhatsApp Web to see full conversation
"""
    return watcher.create_task_file(
        task_id=task_id,
        metadata=metadata,
        content=content,
        destination="inbox",
    )


def check_whatsapp_messages():
    """
    Check WhatsApp for new messages (backward compatibility).
    Reuses the same watcher instance to preserve browser session.
    """
    return _get_watcher().check_for_events()


def run_whatsapp_watcher(poll_interval: int = 10):
    """Run WhatsApp watcher in continuous loop (backward compatibility)."""
    watcher = WhatsAppWatcher(poll_interval=poll_interval)
    watcher.start()


if __name__ == "__main__":
    run_whatsapp_watcher()
