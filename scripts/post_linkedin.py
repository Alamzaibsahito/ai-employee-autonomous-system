"""
LinkedIn Poster using Playwright with Chrome

A reliable LinkedIn posting automation using Playwright sync API with a persistent Chrome profile.
The user logs in manually once, and the session persists for future automated posts.

Usage:
    python scripts/post_linkedin.py --content "Your post content here"
    python scripts/post_linkedin.py -c "Your post content here"

Requirements:
    pip install playwright
    playwright install
"""

import sys
import time
import logging
import argparse
from datetime import datetime
from typing import Optional, Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.error("Playwright not installed. Run: pip install playwright && playwright install")


class LinkedInPoster:
    """
    Posts to LinkedIn using Playwright sync API with a persistent Chrome profile.
    Handles LinkedIn's dynamic UI with multiple fallback selectors.
    """

    LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
    CHROME_PROFILE_PATH = r"C:\chrome-automation-profile"

    # Comprehensive selectors for "Start a post" button
    # LinkedIn uses various structures - we try them all
    START_POST_SELECTORS = [
        # Text-based selectors (most reliable)
        'button:has-text("Start a post")',
        'button:has-text("Start")',
        'span:has-text("Start a post")',
        'div:has-text("Start a post")',
        
        # ARIA label selectors
        '[aria-label="Start a post"]',
        '[aria-label*="Start a post"]',
        '[aria-label*="post"]',
        
        # Button class selectors
        'button.artdeco-button',
        'button.share-box-feed-entry__trigger',
        
        # Role-based selectors
        'div[role="button"]:has-text("Start a post")',
        'div[role="button"][aria-label*="post"]',
        
        # Container-based selectors
        '.share-box-feed-entry__trigger',
        '.share-box-feed-entry__dismissable',
        '.share-box-feed-entry',
        
        # Fallback: any button with "post" text
        'button:has-text("post")',
        'button:has-text("Post")',
    ]

    # Modal dialog selectors (to detect when post dialog is open)
    MODAL_SELECTORS = [
        "div[role='dialog']",
        "div[aria-label*='Create a post']",
        "div[aria-label*='Share']",
        ".artdeco-modal",
        ".artdeco-modal__layer",
        "div[id*='ember']",
    ]

    # Post editor selectors (inside the modal)
    POST_EDITOR_SELECTORS = [
        "div[contenteditable='true']",
        "div[contenteditable='true'][aria-label*='post']",
        "div[contenteditable='true'][placeholder*='post']",
        "div.ql-editor[contenteditable='true']",
        "div.ember-view[contenteditable='true']",
        ".editable-container div[contenteditable='true']",
        "div.AMArticleEditor__contenteditable",
        "div[data-lexical-editor='true']",
    ]

    # Post button selectors
    POST_BUTTON_SELECTORS = [
        'button:has-text("Post")',
        'button:has-text("post")',
        'button.share-actions__primary-action',
        'button[aria-label*="Post"]',
        'button.artdeco-button--primary:has-text("Post")',
        'button.ml2:has-text("Post")',
        'button.artdeco-button--1:has-text("Post")',
    ]

    def __init__(self, profile_path: str = None):
        """
        Initialize the LinkedIn poster.

        Args:
            profile_path: Path to Chrome user data directory
        """
        self.playwright = None
        self.context = None
        self.page = None
        self.profile_path = profile_path or self.CHROME_PROFILE_PATH

    def start(self) -> None:
        """Launch Chrome browser with persistent profile."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install")

        logger.info("Starting Chrome with persistent profile: %s", self.profile_path)

        self.playwright = sync_playwright().start()

        # Launch Chrome with persistent profile
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            channel="chrome",
            headless=False,
            viewport={'width': 1366, 'height': 768},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions-except',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-breakpad',
                '--disable-client-side-phishing-detection',
                '--disable-default-apps',
                '--disable-dev-shm-usage',
                '--disable-features=TranslateUI',
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-renderer-background',
                '--disable-sync',
                '--force-color-profile=srgb',
                '--metrics-recording-only',
                '--no-first-run',
                '--password-store=basic',
                '--use-mock-keychain',
            ],
            ignore_default_args=['--enable-automation'],
            timeout=120000,
        )

        print("Chrome launched")

        # Get or create page
        pages = self.context.pages
        if pages:
            self.page = pages[0]
            # Close any extra pages
            for p in pages[1:]:
                try:
                    p.close()
                except Exception:
                    pass
        else:
            self.page = self.context.new_page()

    def _log_page_state(self) -> None:
        """Log current page state for debugging."""
        try:
            url = self.page.url
            title = self.page.title()
            logger.debug(f"Current URL: {url}")
            logger.debug(f"Current title: {title}")
        except Exception as e:
            logger.debug(f"Could not get page state: {e}")

    def _get_all_buttons_text(self) -> List[str]:
        """Get text content of all buttons on page for debugging."""
        try:
            buttons = self.page.query_selector_all('button')
            texts = []
            for btn in buttons:
                try:
                    text = btn.inner_text(timeout=1000)
                    if text.strip():
                        texts.append(text.strip()[:50])
                except Exception:
                    continue
            return texts
        except Exception:
            return []

    def click_start_post(self) -> bool:
        """
        Click the 'Start a post' button using multiple strategies.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Looking for 'Start a post' button...")
        self._log_page_state()

        # Strategy 0: Try Playwright's get_by_role first (most resilient)
        try:
            import re
            post_button = self.page.get_by_role("button", name=re.compile("post", re.I))
            if post_button.count() > 0 and post_button.is_visible(timeout=2000):
                post_button.scroll_into_view_if_needed(timeout=3000)
                time.sleep(0.5)
                post_button.click(timeout=3000)
                logger.info("Clicked using get_by_role")
                return True
        except Exception as e:
            logger.debug(f"get_by_role failed: {e}")

        # Strategy 1: Try text-based selectors first (most reliable)
        text_selectors = [s for s in self.START_POST_SELECTORS if 'has-text' in s]
        for selector in text_selectors:
            try:
                locator = self.page.locator(selector).first
                count = locator.count()
                logger.debug(f"Trying selector '{selector}' - found {count} element(s)")
                
                if count > 0:
                    if locator.is_visible(timeout=2000):
                        locator.scroll_into_view_if_needed(timeout=3000)
                        time.sleep(0.5)
                        locator.click(timeout=3000)
                        logger.info(f"Clicked using selector: {selector}")
                        return True
            except Exception as e:
                logger.debug(f"Selector failed: {selector} - {e}")
                continue

        # Strategy 2: Try ARIA label selectors
        aria_selectors = [s for s in self.START_POST_SELECTORS if 'aria-label' in s]
        for selector in aria_selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0 and locator.is_visible(timeout=2000):
                    locator.scroll_into_view_if_needed(timeout=3000)
                    time.sleep(0.5)
                    locator.click(timeout=3000)
                    logger.info(f"Clicked using ARIA selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"ARIA selector failed: {selector} - {e}")
                continue

        # Strategy 3: Try class-based selectors
        class_selectors = [s for s in self.START_POST_SELECTORS if '.' in s and 'has-text' not in s]
        for selector in class_selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0 and locator.is_visible(timeout=2000):
                    locator.scroll_into_view_if_needed(timeout=3000)
                    time.sleep(0.5)
                    locator.click(timeout=3000)
                    logger.info(f"Clicked using class selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Class selector failed: {selector} - {e}")
                continue

        # Strategy 4: Find any element containing "Start a post" text
        try:
            logger.debug("Trying XPath to find 'Start a post' text...")
            elements = self.page.query_selector_all('xpath=//*[contains(text(), "Start a post")]')
            for elem in elements:
                try:
                    elem.scroll_into_view_if_needed(timeout=2000)
                    time.sleep(0.3)
                    elem.click(timeout=2000)
                    logger.info("Clicked using XPath text search")
                    return True
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"XPath search failed: {e}")

        # Debug: log all button texts
        button_texts = self._get_all_buttons_text()
        if button_texts:
            logger.info(f"Available buttons on page: {button_texts[:10]}")
        
        logger.error("Could not find 'Start a post' button after trying all strategies")
        return False

    def wait_for_modal(self, timeout: int = 10000) -> bool:
        """
        Wait for the post creation modal dialog to appear.

        Returns:
            True if modal detected, False otherwise
        """
        logger.info("Waiting for post modal dialog...")
        start_time = time.time()
        timeout_seconds = timeout / 1000

        while time.time() - start_time < timeout_seconds:
            for selector in self.MODAL_SELECTORS:
                try:
                    if self.page.is_visible(selector, timeout=1000):
                        logger.debug(f"Modal detected with: {selector}")
                        return True
                except Exception:
                    continue
            
            # Check URL for modal indicators
            current_url = self.page.url
            if "create-post" in current_url.lower() or "share" in current_url.lower():
                logger.debug("Modal detected via URL")
                return True
                
            time.sleep(0.5)

        logger.warning("Modal dialog not detected")
        return False

    def wait_for_editor(self) -> Optional[object]:
        """
        Wait for the post editor to appear.

        Returns:
            Editor locator if found, None otherwise
        """
        logger.info("Waiting for post editor...")

        # Wait for modal first
        self.wait_for_modal(timeout=10000)
        
        # Extra wait for modal animation
        time.sleep(2)

        # Try each editor selector
        for selector in self.POST_EDITOR_SELECTORS:
            try:
                logger.debug(f"Trying editor selector: {selector}")
                self.page.wait_for_selector(selector, timeout=3000)
                locator = self.page.locator(selector).first
                if locator.is_visible(timeout=1000):
                    logger.info(f"Found editor with: {selector}")
                    return locator
            except Exception as e:
                logger.debug(f"Editor selector failed: {selector} - {e}")
                continue

        # Fallback: any contenteditable
        try:
            logger.debug("Trying generic [contenteditable] selector")
            self.page.wait_for_selector("[contenteditable]", timeout=5000)
            locator = self.page.locator("[contenteditable]").first
            if locator.is_visible(timeout=1000):
                logger.info("Found generic contenteditable")
                return locator
        except Exception as e:
            logger.debug(f"Generic selector failed: {e}")

        logger.error("Could not find post editor")
        return None

    def type_post_content(self, editor: object, content: str) -> bool:
        """Type the post content into the editor."""
        try:
            editor.click(timeout=5000)
            time.sleep(0.5)

            # Clear existing content
            try:
                self.page.keyboard.press('Control+A')
                time.sleep(0.3)
                self.page.keyboard.press('Delete')
                time.sleep(0.3)
            except Exception:
                pass

            # Type content
            editor.fill(content)
            time.sleep(0.5)

            logger.info("Post content entered")
            return True
        except Exception as e:
            logger.error(f"Failed to type content: {e}")
            return False

    def click_post_button(self) -> bool:
        """Click the 'Post' button to publish."""
        logger.info("Looking for 'Post' button...")

        for selector in self.POST_BUTTON_SELECTORS:
            try:
                locator = self.page.locator(selector).last
                if locator.count() > 0:
                    if locator.is_visible(timeout=2000):
                        if not locator.is_disabled(timeout=1000):
                            locator.scroll_into_view_if_needed(timeout=3000)
                            time.sleep(0.5)
                            locator.click(timeout=5000)
                            logger.info(f"Clicked Post button with: {selector}")
                            return True
            except Exception as e:
                logger.debug(f"Post button selector failed: {selector} - {e}")
                continue

        logger.error("Could not find 'Post' button")
        return False

    def verify_post_submitted(self) -> bool:
        """Verify the post was submitted successfully."""
        try:
            time.sleep(3)
            
            success_indicators = ["Your post was sent", "post was sent", "See your post"]
            page_content = self.page.content()
            
            for indicator in success_indicators:
                if indicator.lower() in page_content.lower():
                    return True

            error_indicators = ["Something went wrong", "Unable to post", "Try again"]
            for indicator in error_indicators:
                if indicator.lower() in page_content.lower():
                    return False

            return True
        except Exception as e:
            logger.error(f"Failed to verify: {e}")
            return False

    def save_screenshot(self, name: str = "debug") -> str:
        """Save a screenshot for debugging."""
        filename = f"linkedin_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        try:
            self.page.screenshot(path=filename)
            logger.info(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    def _check_if_logged_in(self) -> bool:
        """Check if user is logged in to LinkedIn."""
        current_url = self.page.url
        logger.debug(f"Current URL: {current_url}")
        
        # Detect login page
        login_indicators = [
            "/login",
            "/checkpoint",
            "linkedin.com/signup",
        ]
        for indicator in login_indicators:
            if indicator in current_url.lower():
                logger.error("Detected login page - user not logged in")
                return False
        
        # Detect feed page (logged in)
        feed_indicators = [
            "/feed",
            "/mynetwork",
            "/jobs",
            "/messaging",
            "/notifications",
        ]
        for indicator in feed_indicators:
            if indicator in current_url.lower():
                return True
        
        return True  # Assume logged in if no login indicators

    def create_post(self, content: str) -> Tuple[bool, str, Optional[str]]:
        """
        Create and publish a LinkedIn post.

        Args:
            content: The post content

        Returns:
            Tuple of (success, message, post_id)
        """
        try:
            print("Opening LinkedIn feed")
            logger.info("Navigating to LinkedIn feed...")

            # Navigate to feed with timeout protection
            self.page.goto(self.LINKEDIN_FEED_URL, wait_until='domcontentloaded', timeout=60000)
            
            # Debug: log current URL
            logger.debug(f"Page URL after navigation: {self.page.url}")

            # Check if logged in
            if not self._check_if_logged_in():
                self.save_screenshot("not_logged_in")
                return False, "Not logged in to LinkedIn. Please login manually.", None

            # Wait for feed content instead of networkidle (LinkedIn never reaches networkidle)
            logger.info("Waiting for feed content to load...")
            feed_loaded = False
            
            # Primary: wait for feed posts container
            try:
                self.page.wait_for_selector("div.feed-shared-update-v2", timeout=15000)
                feed_loaded = True
                logger.info("Feed posts container found")
            except PlaywrightTimeoutError:
                logger.debug("Primary feed selector not found, trying fallbacks...")
            
            # Fallback 1: wait for post box container
            if not feed_loaded:
                try:
                    self.page.wait_for_selector("div.share-box-feed-entry", timeout=10000)
                    feed_loaded = True
                    logger.info("Post box container found")
                except PlaywrightTimeoutError:
                    logger.debug("Post box selector not found, trying fallback...")
            
            # Fallback 2: wait for any feed-related element
            if not feed_loaded:
                try:
                    self.page.wait_for_selector("div.feed", timeout=10000)
                    feed_loaded = True
                    logger.info("Generic feed container found")
                except PlaywrightTimeoutError:
                    logger.warning("Could not detect feed content, proceeding anyway...")

            # Take screenshot for debugging
            self.save_screenshot("feed_loaded")
            logger.debug(f"Current page URL: {self.page.url}")

            print("LinkedIn feed loaded")
            logger.info("LinkedIn feed loaded")

            # Wait for stability
            time.sleep(2)

            # Click Start a post
            if not self.click_start_post():
                self.save_screenshot("start_post_failed")
                return False, "Could not find 'Start a post' button", None

            print("Start post clicked")
            logger.info("'Start a post' button clicked")

            time.sleep(2)

            # Wait for editor
            editor = self.wait_for_editor()
            if not editor:
                self.save_screenshot("editor_failed")
                return False, "Could not find post editor", None

            print("Editor detected")
            logger.info("Post editor detected")

            time.sleep(1)

            # Type content
            print("Content typed")
            if not self.type_post_content(editor, content):
                return False, "Failed to type post content", None

            time.sleep(2)

            # Click Post button
            if not self.click_post_button():
                self.save_screenshot("post_button_failed")
                return False, "Could not find 'Post' button", None

            print("Post button clicked")
            logger.info("'Post' button clicked")

            time.sleep(3)

            if not self.verify_post_submitted():
                return False, "Post may not have been submitted", None

            print("Post successfully submitted")
            logger.info("Post successfully submitted")

            post_id = f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return True, "LinkedIn post published successfully", post_id

        except PlaywrightTimeoutError as e:
            self.save_screenshot("timeout")
            logger.error(f"Timeout: {e}")
            return False, f"Timeout: {str(e)}", None
        except Exception as e:
            self.save_screenshot("error")
            logger.error(f"Error: {e}")
            return False, f"Error: {str(e)}", None

    def close(self) -> None:
        """Close browser."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


def post_to_linkedin(content: str, profile_path: str = None) -> Tuple[bool, str, Optional[str]]:
    """Main function to post to LinkedIn."""
    poster = LinkedInPoster(profile_path=profile_path)

    try:
        poster.start()

        # Wait for manual login if needed
        print("\n" + "=" * 60)
        print("IMPORTANT: If not logged in, please login to LinkedIn now.")
        print("Waiting 15 seconds before proceeding...")
        print("=" * 60 + "\n")

        time.sleep(15)

        success, message, post_id = poster.create_post(content)

        if success:
            logger.info("Post complete: %s", message)
        else:
            logger.error("Post failed: %s", message)

        return success, message, post_id

    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return False, f"Error: {str(e)}", None

    finally:
        print("\n" + "=" * 60)
        print("Browser will remain open. Close manually or press Ctrl+C.")
        print("=" * 60 + "\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Closing browser...")
            poster.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Post to LinkedIn from terminal')
    parser.add_argument('--content', '-c', type=str, required=True, help='Post content')
    
    args = parser.parse_args()
    content = args.content

    print("=" * 60)
    print("LinkedIn Auto-Poster")
    print("=" * 60)
    print(f"Content: {content[:100]}{'...' if len(content) > 100 else ''}")
    print(f"Profile: C:\\chrome-automation-profile")
    print("=" * 60 + "\n")

    try:
        success, message, post_id = post_to_linkedin(content)

        if success:
            print(f"\n✓ SUCCESS: {message}")
            if post_id:
                print(f"  Post ID: {post_id}")
        else:
            print(f"\n✗ FAILED: {message}")
            print("\nTroubleshooting:")
            print("  1. Ensure you're logged in to LinkedIn")
            print("  2. Close LinkedIn and try again")
            print("  3. Check for debug screenshots")

    except KeyboardInterrupt:
        print("\nInterrupted")


if __name__ == "__main__":
    main()
