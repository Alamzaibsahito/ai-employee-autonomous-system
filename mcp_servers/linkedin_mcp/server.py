"""
LinkedIn MCP Server — Exposes LinkedIn operations via MCP protocol.

Gold-level features:
- Auto-generate posts using AI
- Schedule posts for future publishing
- Store drafts in vault (/Drafts)
- Require approval before posting
- Track posting history

Tools: search_people, send_connection_request, send_message, get_profile,
       post_update (approval-gated), generate_post, schedule_post, list_drafts, get_post_history
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from playwright.async_api import async_playwright
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp_servers.shared.auth import get_chrome_options

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log

app = Server("linkedin-mcp")

# Session state
_browser = None
_context = None
_page = None

# Gold-level: Post history tracking
POST_HISTORY_FILE = FOLDERS["logs"] / "linkedin_post_history.json"


# ─── Helpers ───────────────────────────────────────────────────────────

def _ensure_linkedin_folders():
    """Ensure LinkedIn-related folders exist."""
    FOLDERS["drafts"].mkdir(parents=True, exist_ok=True)
    FOLDERS["content"].mkdir(parents=True, exist_ok=True)


def _load_post_history() -> list[dict]:
    """Load LinkedIn post history."""
    if POST_HISTORY_FILE.exists():
        with open(POST_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def _save_post_history(history: list[dict]):
    """Save LinkedIn post history."""
    with open(POST_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def _count_posts_today() -> int:
    """Count posts published today."""
    history = _load_post_history()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return sum(1 for p in history if p.get("published_at", "").startswith(today))


def _generate_post_id(text: str) -> str:
    """Generate unique post ID."""
    return f"LI_{hashlib.md5(text.encode()).hexdigest()[:8].upper()}"


def _save_draft(post_id: str, text: str, topic: str = "", scheduled_for: str = "") -> str:
    """Save a post draft to the vault."""
    _ensure_linkedin_folders()
    draft_file = FOLDERS["drafts"] / f"{post_id}.md"

    content = f"""---
type: linkedin_draft
post_id: {post_id}
created: {datetime.now(timezone.utc).isoformat()}
status: draft
topic: {topic}
scheduled_for: {scheduled_for}
approved: false
---

# LinkedIn Draft: {post_id}

**Topic:** {topic or 'General'}
**Created:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
{f"**Scheduled for:** {scheduled_for}" if scheduled_for else ""}

## Content

{text}

## Actions
> - Approve: Change `approved: false` → `approved: true` and run `python main.py approve {post_id}`
> - Edit: Modify the content above
> - Schedule: Set `scheduled_for` to desired ISO timestamp
"""
    with open(draft_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"LinkedIn: Draft saved: {post_id}")
    return str(draft_file)


async def get_linkedin_page():
    """Get or create LinkedIn page with active session."""
    global _browser, _context, _page

    if _page:
        try:
            await _page.evaluate("1")  # Test if page is alive
            return _page
        except Exception:
            pass

    opts = get_chrome_options()
    playwright = await async_playwright().start()

    if config.linkedin_session_path.exists():
        _browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.linkedin_session_path),
            headless=config.linkedin_headless,
        )
        _context = _browser
    else:
        _browser = await playwright.chromium.launch(headless=config.linkedin_headless)
        _context = await _browser.new_context()

    pages = _context.pages
    if pages:
        _page = pages[0]
    else:
        _page = await _context.new_page()

    await _page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=30000)
    return _page


# ─── Existing Tools (unchanged) ────────────────────────────────────────

@app.tool(name="search_people")
async def handle_search_people(keywords: str, limit: int = 10) -> list[TextContent]:
    """Search for people on LinkedIn by keywords. Returns list of profile URLs and names."""
    try:
        page = await get_linkedin_page()
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        results = await page.evaluate("""() => {
            const cards = document.querySelectorAll('.search-results-container li, .reusable-search__result-container');
            return Array.from(cards.slice(0, 10)).map(card => ({
                name: card.querySelector('a span[aria-hidden]')?.textContent?.trim() || '',
                title: card.querySelector('.entity-result__primary-subtitle')?.textContent?.trim() || '',
                url: card.querySelector('a[href*="/in/"]')?.href || ''
            })).filter(r => r.url);
        }""")
        return [TextContent(type="text", text=str(results))]
    except Exception as e:
        logger.error(f"LinkedIn search_people error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="send_connection_request")
async def handle_send_connection(profile_url: str, message: str = "") -> list[TextContent]:
    """Send a connection request to a LinkedIn profile. Requires approval for new contacts."""
    try:
        page = await get_linkedin_page()
        await page.goto(profile_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        clicked = await page.evaluate("""(msg) => {
            const connectBtn = document.querySelector('button[data-control-name="connect"]')
                || document.querySelector('button[data-control-name*="connect"]')
                || Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Connect');
            if (connectBtn) { connectBtn.click(); return 'clicked'; }
            return 'not_found';
        }""", message)

        return [TextContent(type="text", text=f"Connection request interaction: {clicked}")]
    except Exception as e:
        logger.error(f"LinkedIn send_connection_request error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="send_message")
async def handle_send_message(profile_url: str, message: str) -> list[TextContent]:
    """Send a message to a LinkedIn connection."""
    try:
        page = await get_linkedin_page()
        await page.goto(profile_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        result = await page.evaluate("""(msg) => {
            const msgBtn = Array.from(document.querySelectorAll('a, button'))
                .find(el => el.textContent.trim() === 'Message');
            if (msgBtn) { msgBtn.click(); return 'messaging_opened'; }
            return 'no_message_button';
        }""", message)

        return [TextContent(type="text", text=f"Message interaction result: {result}")]
    except Exception as e:
        logger.error(f"LinkedIn send_message error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.tool(name="get_profile")
async def handle_get_profile(profile_url: str) -> list[TextContent]:
    """Get profile information from a LinkedIn URL."""
    try:
        page = await get_linkedin_page()
        await page.goto(profile_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        profile = await page.evaluate("""() => {
            const nameEl = document.querySelector('.text-heading-xlarge');
            const headlineEl = document.querySelector('.text-body-medium');
            const aboutEl = document.querySelector('#about p');
            return {
                name: nameEl?.textContent?.trim() || '',
                headline: headlineEl?.textContent?.trim() || '',
                about: aboutEl?.textContent?.trim() || ''
            };
        }""")
        return [TextContent(type="text", text=str(profile))]
    except Exception as e:
        logger.error(f"LinkedIn get_profile error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ─── Gold-Level: Post Update (Approval-Gated) ──────────────────────────

@app.tool(name="post_update")
async def handle_post_update(text: str, image_url: str = "") -> list[TextContent]:
    """
    Post an update to LinkedIn feed.
    Gold-level: Always saves draft first, requires approval before publishing.
    """
    try:
        _ensure_linkedin_folders()

        # Check daily post limit
        posts_today = _count_posts_today()
        max_posts = config.linkedin_max_posts_per_day
        if posts_today >= max_posts:
            return [TextContent(
                type="text",
                text=f"Daily post limit reached ({posts_today}/{max_posts}). Try again tomorrow."
            )]

        # Generate post ID and save as draft
        post_id = _generate_post_id(text)
        draft_path = _save_draft(post_id, text, topic="Direct post", scheduled_for="")

        # Create approval task in Pending_Approval
        approval_file = FOLDERS["pending_approval"] / f"{post_id}.md"
        content = f"""---
task_id: {post_id}
source: linkedin_mcp
created: {datetime.now(timezone.utc).isoformat()}
status: pending_approval
approval_status: pending
approval_reason: LinkedIn post requires review before publishing
post_type: linkedin_update
draft_path: {draft_path}
---

# ⏳ Approval Required: LinkedIn Post {post_id}

**Submitted:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Reason:** LinkedIn post requires human review before publishing

## Post Content

{text}

{f"**Image:** {image_url}" if image_url else ""}

## Draft
Full draft: `{draft_path}`

## How to Approve
> [!APPROVAL] Run: `python main.py approve {post_id}`
> Or: `python main.py reject {post_id}`
"""
        with open(approval_file, "w", encoding="utf-8") as f:
            f.write(content)

        audit_log(
            action="linkedin_post_submitted_for_approval",
            task_id=post_id,
            details={"topic": "Direct post", "draft": str(draft_path)},
        )

        return [TextContent(
            type="text",
            text=f"Post saved as draft ({post_id}) and submitted for approval. "
                 f"Draft: {draft_path}. Run 'python main.py approve {post_id}' to publish."
        )]
    except Exception as e:
        logger.error(f"LinkedIn post_update error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ─── Gold-Level: AI Post Generation ────────────────────────────────────

@app.tool(name="generate_post")
async def handle_generate_post(topic: str, tone: str = "professional", length: str = "medium") -> list[TextContent]:
    """
    Generate a LinkedIn post using AI based on topic.
    Saves draft to vault for review. Does NOT publish automatically.

    Args:
        topic: What the post should be about
        tone: professional, casual, thought_leader, promotional
        length: short (1-2 paras), medium (3-4), long (5+)
    """
    _ensure_linkedin_folders()

    # Try AI generation if API key available
    ai_text = _generate_ai_post(topic, tone, length)

    if not ai_text:
        # Fallback: use template
        ai_text = _generate_template_post(topic, tone, length)

    post_id = _generate_post_id(ai_text)
    draft_path = _save_draft(post_id, ai_text, topic=topic)

    return [TextContent(
        type="text",
        text=f"Post generated and saved as draft: {post_id}\n\n{ai_text}\n\nDraft: {draft_path}\n"
             f"Run 'python main.py approve {post_id}' to publish."
    )]


def _generate_ai_post(topic: str, tone: str, length: str) -> str:
    """Generate post using Claude/OpenAI."""
    if config.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=f"You are a LinkedIn content writer. Write in a {tone} tone. Length: {length}.",
                messages=[{"role": "user", "content": f"Write an engaging LinkedIn post about: {topic}"}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Claude post generation error: {e}")
    elif config.openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are a LinkedIn content writer. Tone: {tone}. Length: {length}."},
                    {"role": "user", "content": f"Write an engaging LinkedIn post about: {topic}"},
                ],
                max_tokens=512,
            )
            return response.choices[0].message.content if response.choices else ""
        except Exception as e:
            logger.error(f"OpenAI post generation error: {e}")
    return ""


def _generate_template_post(topic: str, tone: str, length: str) -> str:
    """Generate a template post when AI is unavailable."""
    templates = {
        "short": f"💡 Quick thought: {topic}\n\nWhat's your take on this? Share your thoughts below. 👇\n\n#ThoughtLeadership #Industry",
        "medium": f"I've been thinking a lot about {topic} lately.\n\nHere's what I've learned:\n\n1️⃣ It's more important than most people realize\n2️⃣ The landscape is changing rapidly\n3️⃣ Those who adapt early will have a massive advantage\n\nWhat's been your experience with {topic}? I'd love to hear your perspective.\n\n#ProfessionalDevelopment #Insights #Growth",
        "long": f"📖 Deep dive into {topic}\n\nAfter years of working in this space, here are my key insights:\n\n🔹 The fundamentals haven't changed, but the tools have\n🔹 Most people overcomplicate it\n🔹 The winners focus on execution, not perfection\n🔹 Data-driven decisions beat gut feeling 9/10 times\n\nHere's my recommendation:\nStart small. Test everything. Scale what works.\n\nWhat would you add to this list? Drop your insights below 👇\n\n#ThoughtLeadership #Strategy #ProfessionalGrowth #Industry",
    }
    return templates.get(length, templates["medium"])


# ─── Gold-Level: Schedule Post ─────────────────────────────────────────

@app.tool(name="schedule_post")
async def handle_schedule_post(post_id: str, scheduled_for: str) -> list[TextContent]:
    """
    Schedule an existing draft for future publishing.
    scheduled_for: ISO timestamp (e.g. 2025-01-20T09:00:00+00:00)
    """
    _ensure_linkedin_folders()
    draft_file = FOLDERS["drafts"] / f"{post_id}.md"

    if not draft_file.exists():
        return [TextContent(type="text", text=f"Draft not found: {post_id}")]

    try:
        content = draft_file.read_text(encoding="utf-8")
        # Update scheduled_for field
        content = content.replace("scheduled_for: ", f"scheduled_for: {scheduled_for}")
        draft_file.write_text(content, encoding="utf-8")

        # Parse the timestamp for validation
        scheduled_dt = datetime.fromisoformat(scheduled_for)
        if scheduled_dt < datetime.now(timezone.utc):
            return [TextContent(type="text", text="Cannot schedule post in the past.")]

        audit_log(
            action="linkedin_post_scheduled",
            task_id=post_id,
            details={"scheduled_for": scheduled_for},
        )

        return [TextContent(
            type="text",
            text=f"Post {post_id} scheduled for {scheduled_for}"
        )]
    except Exception as e:
        logger.error(f"LinkedIn schedule_post error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ─── Gold-Level: List Drafts ───────────────────────────────────────────

@app.tool(name="list_drafts")
async def handle_list_drafts(status_filter: str = "all") -> list[TextContent]:
    """
    List all LinkedIn post drafts.
    status_filter: all, draft, approved, scheduled
    """
    _ensure_linkedin_folders()
    drafts = []

    for draft_file in FOLDERS["drafts"].glob("*.md"):
        content = draft_file.read_text(encoding="utf-8")

        # Extract metadata
        post_id = ""
        status = "draft"
        scheduled = ""
        topic = ""

        if "---" in content:
            parts = content.split("---", 2)
            if len(parts) >= 2:
                import yaml
                try:
                    meta = yaml.safe_load(parts[1])
                    post_id = meta.get("post_id", draft_file.stem)
                    status = meta.get("status", "draft")
                    scheduled = meta.get("scheduled_for", "")
                    topic = meta.get("topic", "")
                except Exception:
                    post_id = draft_file.stem

        # Filter
        if status_filter == "scheduled" and not scheduled:
            continue
        if status_filter == "approved" and status != "approved":
            continue

        drafts.append({
            "post_id": post_id,
            "status": status,
            "topic": topic,
            "scheduled_for": scheduled,
            "file": str(draft_file),
        })

    return [TextContent(type="text", text=json.dumps(drafts, indent=2))]


# ─── Gold-Level: Publish Approved Post ─────────────────────────────────

@app.tool(name="publish_approved_post")
async def handle_publish_approved_post(post_id: str) -> list[TextContent]:
    """
    Publish an approved LinkedIn post.
    Reads the draft file, verifies approval, then posts via browser automation.
    """
    _ensure_linkedin_folders()
    draft_file = FOLDERS["drafts"] / f"{post_id}.md"

    if not draft_file.exists():
        return [TextContent(type="text", text=f"Draft not found: {post_id}")]

    # Read draft and verify approval
    content = draft_file.read_text(encoding="utf-8")

    # Extract post text (between "## Content" and "## Actions")
    if "## Content" in content and "## Actions" in content:
        post_text = content.split("## Content")[1].split("## Actions")[0].strip()
    else:
        return [TextContent(type="text", text="Could not extract post content from draft")]

    # Check approval status
    approved = "approved: true" in content.lower()
    if not approved:
        return [TextContent(
            type="text",
            text=f"Post {post_id} is not approved yet. Run 'python main.py approve {post_id}' first."
        )]

    # Check daily limit
    posts_today = _count_posts_today()
    max_posts = config.linkedin_max_posts_per_day
    if posts_today >= max_posts:
        return [TextContent(
            type="text",
            text=f"Daily post limit reached ({posts_today}/{max_posts})."
        )]

    # Publish via browser
    try:
        page = await get_linkedin_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Click "Start a post"
        await page.evaluate("""() => {
            const startPost = Array.from(document.querySelectorAll('button, div[role="button"]'))
                .find(el => el.textContent.includes('Start a post'));
            if (startPost) startPost.click();
        }""")
        await page.wait_for_timeout(2000)

        # Type the post text
        text_selector = "div[role='textbox'][aria-label='Write an article']"
        await page.wait_for_selector(text_selector, timeout=10000)
        await page.fill(text_selector, post_text)
        await page.wait_for_timeout(1000)

        # Click Post button
        await page.evaluate("""() => {
            const postBtn = Array.from(document.querySelectorAll('button'))
                .find(el => el.textContent.trim() === 'Post');
            if (postBtn) postBtn.click();
        }""")

        # Record in history
        history = _load_post_history()
        history.append({
            "post_id": post_id,
            "text_preview": post_text[:100] + "...",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "status": "published",
        })
        _save_post_history(history)

        # Update draft status
        content = content.replace("status: draft", "status: published")
        content = content.replace(f"approved: true", f"approved: true\npublished_at: {datetime.now(timezone.utc).isoformat()}")
        draft_file.write_text(content, encoding="utf-8")

        # Move to Content folder
        content_file = FOLDERS["content"] / f"{post_id}_published.md"
        draft_file.rename(content_file)

        audit_log(
            action="linkedin_post_published",
            task_id=post_id,
            details={"text_preview": post_text[:100]},
        )

        return [TextContent(type="text", text=f"✅ Post {post_id} published successfully!")]

    except Exception as e:
        logger.error(f"LinkedIn publish error: {e}")
        return [TextContent(type="text", text=f"Error publishing: {str(e)}")]


# ─── Gold-Level: Post History ──────────────────────────────────────────

@app.tool(name="get_post_history")
async def handle_get_post_history(limit: int = 10) -> list[TextContent]:
    """Get recent LinkedIn post history."""
    history = _load_post_history()
    return [TextContent(type="text", text=json.dumps(history[-limit:], indent=2))]


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run())

