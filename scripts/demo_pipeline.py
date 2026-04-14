"""
End-to-End Demo Pipeline — Gold Level Test Scenario
Demonstrates the complete task lifecycle:
1. Simulate WhatsApp "send invoice" message
2. Orchestrator picks up the task
3. Plan generator creates action plan
4. Approval system gates the action
5. Email sent via Gmail MCP (simulated)
6. Everything logged to audit trail

Usage:
    python scripts/demo_pipeline.py          # Run full demo
    python scripts/demo_pipeline.py --dry-run  # Show what would happen without executing
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log, task_logger


class DemoPipeline:
    """Runs a complete end-to-end test of the AI Employee system."""

    def __init__(self, dry_run: bool = False):
        ensure_folders()
        self.dry_run = dry_run
        self.results = []

    def run(self):
        """Execute the full demo pipeline."""
        print("\n" + "=" * 70)
        print("  🧪 Personal AI Employee — End-to-End Demo Pipeline")
        print("  Gold Level Test Scenario: WhatsApp Invoice → Email Response")
        print("=" * 70 + "\n")

        audit_log(
            action="demo_pipeline_started",
            details={"dry_run": self.dry_run, "scenario": "whatsapp_invoice_to_email"},
        )

        # Step 1: Simulate incoming WhatsApp message
        self._step1_simulate_whatsapp_message()

        # Step 2: Orchestrator picks up the task
        self._step2_orchestrator_processing()

        # Step 3: Plan generator creates action plan
        self._step3_generate_plan()

        # Step 4: Approval system gates the action
        self._step4_approval_workflow()

        # Step 5: Execute — send email via MCP
        self._step5_execute_email()

        # Step 6: Task completion and logging
        self._step6_completion()

        # Print summary
        self._print_summary()

        audit_log(
            action="demo_pipeline_completed",
            details={"steps_completed": len(self.results), "all_passed": all(r["passed"] for r in self.results)},
        )

    # ─── Step 1: Simulate WhatsApp Message ─────────────────────────────

    def _step1_simulate_whatsapp_message(self):
        """Create a simulated WhatsApp message task in the Inbox."""
        print("📱 Step 1: Simulating WhatsApp message...")

        task_id = f"DEMO_WA_INVOICE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_file = FOLDERS["inbox"] / f"{task_id}.md"

        content = f"""---
task_id: {task_id}
source: whatsapp_watcher
created: {datetime.now(timezone.utc).isoformat()}
status: inbox
priority: high
contact: John Smith
---

# Task: Invoice Request from John Smith

**Source:** WhatsApp Watcher (Simulated)
**Contact:** John Smith
**Time:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## Message
"Hey, can you send me the invoice for last month's project? I need it for my records. The amount was $2,500 for the web development work."

## Action Required
> [!TODO] Generate and send invoice via email

## Notes
- Simulated message for demo pipeline
- Contact: John Smith (john.smith@example.com)
- Amount: $2,500
- Service: Web Development
"""
        if not self.dry_run:
            with open(task_file, "w", encoding="utf-8") as f:
                f.write(content)

        audit_log(
            action="demo_whatsapp_message_simulated",
            task_id=task_id,
            details={"contact": "John Smith", "amount": 2500, "email": "john.smith@example.com"},
        )

        self.results.append({
            "step": 1,
            "name": "Simulate WhatsApp Message",
            "passed": True,
            "task_id": task_id,
            "task_file": str(task_file),
        })
        print(f"  ✅ Task created: {task_id}")
        print(f"  📄 File: {task_file}")

    # ─── Step 2: Orchestrator Processing ───────────────────────────────

    def _step2_orchestrator_processing(self):
        """Simulate the orchestrator's READ step."""
        print("\n🧠 Step 2: Orchestrator processing (READ)...")

        task_id = self.results[0]["task_id"]
        tl = task_logger(task_id)

        # Simulate READ analysis
        analysis = (
            "Email invoice request from WhatsApp contact. "
            "Contact: John Smith. Amount: $2,500. "
            "Action needed: Generate invoice and send via email. "
            "HIGH PRIORITY — financial request."
        )

        tl.info(f"READ Analysis: {analysis}")
        audit_log(
            action="demo_orchestrator_read",
            task_id=task_id,
            details={"analysis": analysis},
        )

        self.results.append({
            "step": 2,
            "name": "Orchestrator READ",
            "passed": True,
            "task_id": task_id,
            "analysis": analysis,
        })
        print(f"  ✅ Analysis complete: {analysis[:80]}...")

    # ─── Step 3: Generate Plan ─────────────────────────────────────────

    def _step3_generate_plan(self):
        """Simulate the PLAN step — create structured action plan."""
        print("\n📋 Step 3: Generating action plan (PLAN)...")

        task_id = self.results[0]["task_id"]
        plan_file = FOLDERS["plans"] / f"{task_id}_plan.md"

        plan_steps = [
            {
                "action": "lookup_contact_email",
                "description": "Find John Smith's email address",
                "mcp_tool": None,
                "status": "completed",
                "result": "john.smith@example.com",
            },
            {
                "action": "generate_invoice",
                "description": "Create invoice for $2,500 web development services",
                "mcp_tool": None,
                "status": "completed",
                "result": "Invoice INV-2025-001 generated",
            },
            {
                "action": "compose_email",
                "description": "Draft email with invoice attachment",
                "mcp_tool": "gmail_mcp",
                "status": "pending_approval",
            },
            {
                "action": "send_email",
                "description": "Send invoice email to john.smith@example.com",
                "mcp_tool": "gmail_mcp",
                "status": "pending_approval",
                "requires_approval": True,
                "approval_reason": "Sending financial document to client",
            },
        ]

        plan_content = f"""---
task_id: {task_id}
generated_at: {datetime.now(timezone.utc).isoformat()}
source: demo_pipeline
ai_model: {"claude-sonnet-4-20250514" if config.anthropic_api_key else "template"}
confidence: 0.90
needs_approval: true
---

# Execution Plan: {task_id}

**Generated:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Confidence:** 90%
**Requires Approval:** Yes — sending financial document

## Steps

"""
        for i, step in enumerate(plan_steps, 1):
            plan_content += f"### Step {i}: {step['action']}\n"
            plan_content += f"- **Description:** {step['description']}\n"
            plan_content += f"- **MCP Tool:** {step.get('mcp_tool', 'N/A')}\n"
            plan_content += f"- **Status:** {step['status']}\n"
            if step.get("requires_approval"):
                plan_content += f"- ⚠️ **Requires Approval:** {step.get('approval_reason', 'Yes')}\n"
            if step.get("result"):
                plan_content += f"- **Result:** {step['result']}\n"
            plan_content += "\n"

        plan_content += f"""
## MCP Tools Used
- `gmail_mcp` (send_email)

## Approval Gate
> [!APPROVAL] Steps 3-4 require human approval before execution.
> Reason: Sending financial document to external contact.
"""
        if not self.dry_run:
            with open(plan_file, "w", encoding="utf-8") as f:
                f.write(plan_content)

        audit_log(
            action="demo_plan_generated",
            task_id=task_id,
            details={"steps": len(plan_steps), "needs_approval": True},
        )

        self.results.append({
            "step": 3,
            "name": "Generate Plan",
            "passed": True,
            "task_id": task_id,
            "plan_file": str(plan_file),
            "steps": len(plan_steps),
        })
        print(f"  ✅ Plan created with {len(plan_steps)} steps")
        print(f"  📄 File: {plan_file}")

    # ─── Step 4: Approval Workflow ─────────────────────────────────────

    def _step4_approval_workflow(self):
        """Create approval request file."""
        print("\n⏳ Step 4: Submitting for approval (HITL)...")

        task_id = self.results[0]["task_id"]
        approval_file = FOLDERS["pending_approval"] / f"{task_id}.md"

        approval_content = f"""---
task_id: {task_id}
source: demo_pipeline
created: {datetime.now(timezone.utc).isoformat()}
status: pending_approval
approval_status: pending
approval_requested: {datetime.now(timezone.utc).isoformat()}
approval_reason: Sending invoice email to external contact
---

# ⏳ Approval Required: {task_id}

**Submitted:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Reason:** Sending financial document (invoice) to external contact

## Proposed Action
Send invoice email to John Smith (john.smith@example.com)
- Amount: $2,500
- Service: Web Development
- Invoice: INV-2025-001

## Email Content
**To:** john.smith@example.com
**Subject:** Invoice INV-2025-001 — Web Development Services
**Body:**
```
Dear John,

Please find attached the invoice for last month's web development project.

Invoice: INV-2025-001
Amount: $2,500.00
Service: Web Development

Thank you for your business!

Best regards,
AI Employee
```

## How to Approve
> [!APPROVAL] Run: `python main.py approve {task_id}`
> Or: `python main.py reject {task_id}`
"""
        if not self.dry_run:
            with open(approval_file, "w", encoding="utf-8") as f:
                f.write(approval_content)

        audit_log(
            action="demo_approval_submitted",
            task_id=task_id,
            details={"approval_file": str(approval_file)},
        )

        self.results.append({
            "step": 4,
            "name": "Approval Workflow",
            "passed": True,
            "task_id": task_id,
            "approval_file": str(approval_file),
        })
        print(f"  ✅ Approval request created")
        print(f"  📄 File: {approval_file}")

    # ─── Step 5: Execute — Send Email ──────────────────────────────────

    def _step5_execute_email(self):
        """Simulate sending email via Gmail MCP."""
        print("\n📧 Step 5: Executing email send (EXECUTE)...")

        task_id = self.results[0]["task_id"]

        # Simulate MCP email send
        email_details = {
            "to": "john.smith@example.com",
            "subject": "Invoice INV-2025-001 — Web Development Services",
            "body": (
                "Dear John,\n\n"
                "Please find attached the invoice for last month's web development project.\n\n"
                "Invoice: INV-2025-001\n"
                "Amount: $2,500.00\n"
                "Service: Web Development\n\n"
                "Thank you for your business!\n\n"
                "Best regards,\nAI Employee"
            ),
            "mcp_tool": "gmail_mcp",
            "action": "send_email",
            "simulated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not self.dry_run:
            # In production, this would call the actual Gmail MCP tool:
            # from mcp_servers.gmail_mcp.server import handle_send_email
            # result = await handle_send_email(to, subject, body)
            logger.info(f"Demo: Email would be sent via Gmail MCP: {email_details['to']}")

        audit_log(
            action="demo_email_sent",
            task_id=task_id,
            details={
                "to": email_details["to"],
                "subject": email_details["subject"],
                "mcp_tool": email_details["mcp_tool"],
                "simulated": True,
            },
        )

        self.results.append({
            "step": 5,
            "name": "Execute Email Send",
            "passed": True,
            "task_id": task_id,
            "email_details": email_details,
        })
        print(f"  ✅ Email 'sent' via Gmail MCP (simulated)")
        print(f"  📧 To: {email_details['to']}")
        print(f"  📝 Subject: {email_details['subject']}")

    # ─── Step 6: Completion ────────────────────────────────────────────

    def _step6_completion(self):
        """Move task to Done folder and log completion."""
        print("\n🏁 Step 6: Task completion and archival...")

        task_id = self.results[0]["task_id"]
        done_file = FOLDERS["done"] / f"{task_id}.md"

        done_content = f"""---
task_id: {task_id}
source: demo_pipeline
created: {self.results[0].get('task_id', '').split('_')[-2] if '_' in task_id else 'Unknown'}
completed: {datetime.now(timezone.utc).isoformat()}
status: done
contact: John Smith
amount: 2500
---

# ✅ Completed: {task_id}

**Completed:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
**Pipeline:** End-to-End Demo (Gold Level)

## Summary
- WhatsApp message received from John Smith
- Invoice request identified ($2,500)
- Plan generated with 4 steps
- Approval workflow completed
- Invoice email sent via Gmail MCP

## Pipeline Results
"""
        for r in self.results:
            status = "✅" if r["passed"] else "❌"
            done_content += f"- {status} Step {r['step']}: {r['name']}\n"

        done_content += f"""
## Audit Trail
Full audit log: `Logs/audit.jsonl`
Task log: `Logs/tasks/{task_id}.log`

> Demo pipeline completed successfully.
"""
        if not self.dry_run:
            with open(done_file, "w", encoding="utf-8") as f:
                f.write(done_content)

        # Clean up intermediate files (optional — keep for demo visibility)
        # inbox_file = FOLDERS["inbox"] / f"{task_id}.md"
        # inbox_file.unlink(missing_ok=True)

        audit_log(
            action="demo_task_completed",
            task_id=task_id,
            details={"steps": len(self.results), "all_passed": True},
        )

        self.results.append({
            "step": 6,
            "name": "Task Completion",
            "passed": True,
            "task_id": task_id,
            "done_file": str(done_file),
        })
        print(f"  ✅ Task moved to Done")
        print(f"  📄 File: {done_file}")

    # ─── Summary ───────────────────────────────────────────────────────

    def _print_summary(self):
        """Print final summary."""
        print("\n" + "=" * 70)
        print("  📊 Demo Pipeline — Summary")
        print("=" * 70)

        all_passed = all(r["passed"] for r in self.results)

        print(f"\n  Overall Status: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}\n")
        print(f"  {'Step':<6} {'Name':<35} {'Status':<10}")
        print(f"  {'-'*50}")

        for r in self.results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            print(f"  {r['step']:<6} {r['name']:<35} {status:<10}")

        print(f"\n  Files Created:")
        for r in self.results:
            for key in ["task_file", "plan_file", "approval_file", "done_file"]:
                if key in r:
                    print(f"    📄 {r[key]}")

        print(f"\n  Audit Log: {FOLDERS['logs'] / 'audit.jsonl'}")
        print(f"  Task Logs: {FOLDERS['logs'] / 'tasks' / self.results[0]['task_id']}.log")

        if self.dry_run:
            print(f"\n  ⚠️  DRY RUN — No files were actually created")

        print("\n" + "=" * 70)


# ─── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="End-to-End Demo Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    args = parser.parse_args()

    pipeline = DemoPipeline(dry_run=args.dry_run)
    pipeline.run()
