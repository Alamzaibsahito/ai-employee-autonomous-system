"""
Plan Generator — Claude Reasoning Output Handler
Takes AI reasoning output and converts it into structured, executable plans.
Serves as the bridge between Claude/OpenAI responses and task execution.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger


class PlanGenerator:
    """Generates structured execution plans from AI reasoning output."""

    def __init__(self):
        ensure_folders()

    def generate_plan(self, task: dict, ai_response: str) -> Optional[dict]:
        """
        Generate a structured plan from AI reasoning output.

        Args:
            task: The original task dict
            ai_response: Raw text response from Claude/OpenAI

        Returns:
            Structured plan dict with steps, confidence, and metadata
        """
        task_id = task.get("task_id", "unknown")
        tl = task_logger(task_id)

        # Parse AI response into steps
        steps = self._parse_steps(ai_response)
        if not steps:
            tl.warning("Could not parse steps from AI response — generating fallback plan")
            steps = self._generate_fallback_plan(task)

        # Extract confidence score
        confidence = self._extract_confidence(ai_response)

        # Identify required MCP tools
        mcp_tools = self._identify_mCP_tools(steps)

        # Check for approval requirements
        needs_approval = self._check_approval_needed(task, steps)

        plan = {
            "task_id": task_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": task.get("source", "unknown"),
            "ai_model": self._detect_ai_model(),
            "confidence": confidence,
            "steps": steps,
            "mcp_tools": mcp_tools,
            "needs_approval": needs_approval,
            "estimated_steps": len(steps),
            "raw_ai_response": ai_response[:2000],  # Truncate for logging
        }

        logger.info(f"Plan generated for {task_id}: {len(steps)} steps, confidence={confidence:.0%}")
        audit_log(
            action="plan_generated",
            task_id=task_id,
            details={"steps": len(steps), "confidence": confidence, "mcp_tools": mcp_tools},
        )

        return plan

    def save_plan(self, plan: dict) -> str:
        """Save plan to Plans folder as markdown file."""
        task_id = plan["task_id"]
        plan_file = FOLDERS["plans"] / f"{task_id}_plan.md"

        content = f"""---
task_id: {task_id}
generated_at: {plan['generated_at']}
source: {plan['source']}
ai_model: {plan['ai_model']}
confidence: {plan['confidence']:.0%}
needs_approval: {plan['needs_approval']}
mcp_tools: {', '.join(plan['mcp_tools'])}
---

# Execution Plan: {task_id}

**Generated:** {datetime.fromisoformat(plan['generated_at']).strftime("%Y-%m-%d %H:%M:%S UTC")}
**AI Model:** {plan['ai_model']}
**Confidence:** {plan['confidence']:.0%}
**Estimated Steps:** {plan['estimated_steps']}

## Steps

"""
        for i, step in enumerate(plan["steps"], 1):
            content += f"### Step {i}: {step['action']}\n"
            content += f"- **Description:** {step.get('description', 'N/A')}\n"
            content += f"- **MCP Tool:** {step.get('mcp_tool', 'N/A')}\n"
            content += f"- **Parameters:** `{json.dumps(step.get('params', {}))}`\n"
            if step.get("requires_approval"):
                content += f"- ⚠️ **Requires Approval:** {step.get('approval_reason', 'Yes')}\n"
            content += "\n"

        content += "## MCP Tools Used\n"
        for tool in plan["mcp_tools"]:
            content += f"- `{tool}`\n"

        content += f"\n## Raw AI Response\n<details>\n<summary>Click to expand</summary>\n\n```\n{plan['raw_ai_response']}\n```\n\n</details>\n"

        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(content)

        return str(plan_file)

    # ─── Parsing ───────────────────────────────────────────────────────

    def _parse_steps(self, ai_response: str) -> list[dict]:
        """Parse numbered/bullet steps from AI response text."""
        steps = []

        # Try numbered pattern: "1. Do something" or "1) Do something"
        numbered_pattern = re.compile(
            r'^\s*(\d+)[.)]\s+(.+?)(?:\n|$)', re.MULTILINE
        )
        matches = numbered_pattern.findall(ai_response)

        if matches:
            for num, desc in matches:
                step = self._normalize_step(desc.strip())
                if step:
                    steps.append(step)
            return steps

        # Try bullet pattern: "- Do something" or "* Do something"
        bullet_pattern = re.compile(
            r'^\s*[-*]\s+(.+?)(?:\n|$)', re.MULTILINE
        )
        matches = bullet_pattern.findall(ai_response)

        if matches:
            for desc in matches:
                step = self._normalize_step(desc.strip())
                if step:
                    steps.append(step)
            return steps

        # Fallback: treat entire response as a single step
        if ai_response.strip():
            return [self._normalize_step(ai_response.strip())]

        return []

    def _normalize_step(self, text: str) -> Optional[dict]:
        """Convert step text into structured step dict."""
        if not text or len(text) < 3:
            return None

        # Try to extract action and details
        action = text
        params = {}

        # Detect MCP tool references
        mcp_tool = None
        tool_patterns = {
            "gmail": ["gmail", "email", "send mail", "read mail"],
            "whatsapp": ["whatsapp", "send message", "chat"],
            "linkedin": ["linkedin", "connection", "profile", "post"],
            "filesystem": ["file", "save", "read file", "download"],
        }

        text_lower = text.lower()
        for tool_name, keywords in tool_patterns.items():
            if any(kw in text_lower for kw in keywords):
                mcp_tool = f"{tool_name}_mcp"
                break

        return {
            "action": action[:100],
            "description": text,
            "mcp_tool": mcp_tool,
            "params": params,
            "requires_approval": False,
        }

    def _generate_fallback_plan(self, task: dict) -> list[dict]:
        """Generate a basic plan when AI response is unparseable."""
        source = task.get("source", "unknown")

        fallback_plans = {
            "gmail_watcher": [
                {"action": "read_email", "description": "Read the email content", "mcp_tool": "gmail_mcp", "params": {}, "requires_approval": False},
                {"action": "analyze", "description": "Analyze email for required actions", "mcp_tool": None, "params": {}, "requires_approval": False},
                {"action": "respond_or_escalate", "description": "Draft response or escalate", "mcp_tool": "gmail_mcp", "params": {}, "requires_approval": True},
            ],
            "whatsapp_watcher": [
                {"action": "read_message", "description": "Read the WhatsApp message", "mcp_tool": "whatsapp_mcp", "params": {}, "requires_approval": False},
                {"action": "generate_response", "description": "Generate appropriate response", "mcp_tool": None, "params": {}, "requires_approval": False},
                {"action": "send_response", "description": "Send response after approval", "mcp_tool": "whatsapp_mcp", "params": {}, "requires_approval": True},
            ],
            "finance_watcher": [
                {"action": "review_transaction", "description": "Review the financial transaction", "mcp_tool": None, "params": {}, "requires_approval": False},
                {"action": "categorize", "description": "Categorize the transaction", "mcp_tool": None, "params": {}, "requires_approval": False},
                {"action": "notify", "description": "Notify user of the transaction", "mcp_tool": "whatsapp_mcp", "params": {}, "requires_approval": True},
            ],
        }

        return fallback_plans.get(source, [
            {"action": "review", "description": "Review the task", "mcp_tool": None, "params": {}, "requires_approval": False},
            {"action": "execute", "description": "Execute required actions", "mcp_tool": None, "params": {}, "requires_approval": True},
        ])

    def _extract_confidence(self, ai_response: str) -> float:
        """Extract confidence score from AI response (0.0 to 1.0)."""
        text = ai_response.lower()

        # Look for explicit confidence mentions
        confidence_patterns = {
            "very confident": 0.95,
            "confident": 0.85,
            "somewhat confident": 0.7,
            "uncertain": 0.5,
            "not sure": 0.4,
            "guess": 0.3,
        }

        for phrase, score in confidence_patterns.items():
            if phrase in text:
                return score

        # Default confidence based on response quality
        if len(ai_response) > 200:
            return 0.8
        elif len(ai_response) > 50:
            return 0.6
        else:
            return 0.4

    def _identify_MCP_tools(self, steps: list[dict]) -> list[str]:
        """Identify which MCP tools are referenced in the plan steps."""
        tools = set()
        for step in steps:
            if step.get("mcp_tool"):
                tools.add(step["mcp_tool"])
        return sorted(tools)

    def _check_approval_needed(self, task: dict, steps: list[dict]) -> bool:
        """Check if any step requires human approval."""
        for step in steps:
            if step.get("requires_approval"):
                return True
            # Check for approval keywords in step
            text = f"{step.get('action', '')} {step.get('description', '')}".lower()
            if any(kw in text for kw in ["approve", "confirm", "review before", "send to", "pay"]):
                return True
        return False

    def _detect_ai_model(self) -> str:
        """Detect which AI model is configured."""
        if config.anthropic_api_key:
            return "claude-sonnet-4-20250514"
        elif config.openai_api_key:
            return "gpt-4o-mini"
        else:
            return "none"


# ─── Module-level convenience ─────────────────────────────────────────

_plan_gen = None


def get_plan_generator() -> PlanGenerator:
    """Singleton accessor."""
    global _plan_gen
    if _plan_gen is None:
        _plan_gen = PlanGenerator()
    return _plan_gen


def generate_plan(task: dict, ai_response: str) -> Optional[dict]:
    """Convenience function to generate a plan."""
    return get_plan_generator().generate_plan(task, ai_response)


def save_plan(plan: dict) -> str:
    """Convenience function to save a plan."""
    return get_plan_generator().save_plan(plan)


if __name__ == "__main__":
    # Test with sample data
    pg = PlanGenerator()
    sample_task = {"task_id": "TEST_001", "source": "gmail_watcher"}
    sample_response = """
    1. Read the email content using Gmail MCP
    2. Analyze the sender and subject for urgency
    3. Draft a professional response
    4. Send response after human approval
    I'm confident this is the right approach.
    """
    plan = pg.generate_plan(sample_task, sample_response)
    if plan:
        path = pg.save_plan(plan)
        print(f"Plan saved to: {path}")
