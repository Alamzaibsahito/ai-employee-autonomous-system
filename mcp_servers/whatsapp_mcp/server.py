"""
WhatsApp MCP Server — Exposes WhatsApp Web operations via MCP protocol.
Tools: send_message, send_message_to_new_contact, read_messages, get_contacts, search_chats
"""

import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from playwright.async_api import async_playwright
from mcp.server import Server
from mcp.types import Tool, TextContent

from config import config
from logger_setup import logger

app = Server("whatsapp-mcp")

# Session state
_browser = None
_context = None
_page = None


async def get_whatsapp_page():
    """Get or create WhatsApp Web page with active session."""
    global _browser, _context, _page

    if _page:
        try:
            await _page.evaluate("1")
            return _page
        except Exception:
            pass

    playwright = await async_playwright().start()

    if config.whatsapp_session_path.exists():
        _context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.whatsapp_session_path),
            headless=config.whatsapp_headless,
        )
        pages = _context.pages
        _page = pages[0] if pages else await _context.new_page()
    else:
        _browser = await playwright.chromium.launch(headless=config.whatsapp_headless)
        _context = await _browser.new_context()
        _page = await _context.new_page()

    await _page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
    # Wait for QR code scan or chat list
    try:
        await _page.wait_for_selector("div[data-testid='chat-list']", timeout=60000)
    except Exception:
        logger.warning("WhatsApp: Chat list not found — session may need re-authentication")

    return _page


@app.tool(name="send_message")
async def handle_send_message(contact: str, message: str) -> list[TextContent]:
    """Send a WhatsApp message to an existing contact. Contact name must match WhatsApp list."""
    try:
        page = await get_whatsapp_page()

        # Search for contact
        search_selector = "div[data-testid='chat-list-header-search']"
        await page.wait_for_selector(search_selector, timeout=10000)
        await page.click(search_selector)
        await page.fill("div[contenteditable='true'][data-tab='3']", contact)
        await page.wait_for_timeout(2000)

        # Click on the contact
        await page.click(f"span[title='{contact}']")
        await page.wait_for_timeout(2000)

        # Type and send message
        await page.click("div[data-testid='conversation-compose-box-input']")
        await page.fill("div[data-testid='conversation-compose-box-input']", message)
        await page.wait_for_timeout(500)
        await page.click("button[data-testid='compose-btn-send']")

        return [TextContent(type="text", text=f"Message sent to {contact}")]
    except Exception as e:
        logger.error(f"WhatsApp send_message error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="send_message_to_new_contact")
async def handle_send_message_new_contact(phone: str, message: str, contact_name: str = "") -> list[TextContent]:
    """Send WhatsApp message to a new contact (not in list). Requires human approval.
    Phone must include country code, e.g. '923001234567'."""
    try:
        # Open direct chat via wa.me link
        page = await get_whatsapp_page()
        await page.goto(f"https://wa.me/{phone}", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Type and send
        compose_box = "div[data-testid='conversation-compose-box-input']"
        await page.wait_for_selector(compose_box, timeout=10000)
        await page.fill(compose_box, message)
        await page.wait_for_timeout(500)
        await page.click("button[data-testid='compose-btn-send']")

        return [TextContent(type="text", text=f"Message sent to new contact +{phone}")]
    except Exception as e:
        logger.error(f"WhatsApp send_message_to_new_contact error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="read_messages")
async def handle_read_messages(contact: str = "", limit: int = 10) -> list[TextContent]:
    """Read recent messages from a WhatsApp chat. If contact is empty, reads from currently open chat."""
    try:
        page = await get_whatsapp_page()

        if contact:
            # Search and open contact
            await page.click("div[data-testid='chat-list-header-search']")
            await page.fill("div[contenteditable='true'][data-tab='3']", contact)
            await page.wait_for_timeout(2000)
            await page.click(f"span[title='{contact}']")
            await page.wait_for_timeout(2000)

        # Extract messages
        messages = await page.evaluate("""() => {
            const msgs = document.querySelectorAll('div[data-testid="conversation-panel-message"]');
            return Array.from(msgs.slice(-20)).map(m => ({
                text: m.getAttribute('data-pre-plain-text') || m.textContent?.trim() || '',
                type: m.classList.contains('message-out') ? 'sent' : 'received',
                timestamp: m.querySelector('span.copyable-text')?.textContent?.trim() || ''
            }));
        }""")
        return [TextContent(type="text", text=str(messages))]
    except Exception as e:
        logger.error(f"WhatsApp read_messages error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="get_contacts")
async def handle_get_contacts() -> list[TextContent]:
    """Get list of visible contacts from WhatsApp sidebar."""
    try:
        page = await get_whatsapp_page()
        contacts = await page.evaluate("""() => {
            const items = document.querySelectorAll('div[data-testid="cell-frame-container"]');
            return Array.from(items).map(item => ({
                name: item.querySelector('span[title]')?.getAttribute('title') || '',
                last_message: item.querySelector('span[data-testid="cell-frame-title"]')?.textContent?.trim() || ''
            })).filter(c => c.name);
        }""")
        return [TextContent(type="text", text=str(contacts))]
    except Exception as e:
        logger.error(f"WhatsApp get_contacts error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="search_chats")
async def handle_search_chats(query: str) -> list[TextContent]:
    """Search WhatsApp chats by contact name or message content."""
    try:
        page = await get_whatsapp_page()
        await page.click("div[data-testid='chat-list-header-search']")
        await page.fill("div[contenteditable='true'][data-tab='3']", query)
        await page.wait_for_timeout(3000)

        results = await page.evaluate("""() => {
            const items = document.querySelectorAll('div[data-testid="cell-frame-container"]');
            return Array.from(items).map(item => ({
                name: item.querySelector('span[title]')?.getAttribute('title') || '',
                last_message: item.querySelector('span[data-testid="cell-frame-title"]')?.textContent?.trim() || ''
            })).filter(c => c.name);
        }""")
        return [TextContent(type="text", text=str(results))]
    except Exception as e:
        logger.error(f"WhatsApp search_chats error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())
