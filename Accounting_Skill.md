---
Type: agent_skill
Status: active
Version: 1.0
Created_at: 2026-02-18
---

# Accounting Skill (Gold Tier)

## 1. Skill Name

**Accounting**

## 2. Purpose

The Accounting skill is a lightweight vault-based accounting system that automatically tracks business-related actions by updating markdown ledger files. It provides real-time financial tracking without requiring external accounting software.

**Goal in simple terms:** Business action detected → Record entry → Update ledgers → Generate weekly summary

**Core capabilities:**
- Automatic detection of income, expenses, and invoices
- Markdown-based ledger files for transparency
- Weekly summary generation with CEO briefings
- Error handling without workflow interruption
- Integration with existing task workflow

## 3. Trigger Conditions

The accounting system activates when:

| Trigger | Description |
|---------|-------------|
| **Task Processing** | Task content contains business keywords (payment, invoice, expense) |
| **MCP Actions** | External actions via MCP servers involve financial transactions |
| **Manual Entry** | Direct function calls to accounting module |
| **Scheduled Summary** | Weekly summary generation (every Monday or on-demand) |

### Business Action Keywords

#### Income Keywords
- payment received, income, revenue, sale, invoice paid
- client payment, customer payment, deposit, refund received
- subscription, service fee, consulting fee, project payment
- milestone payment, retainer, commission, royalty

#### Expense Keywords
- expense, payment made, purchase, cost, bill, invoice
- vendor payment, supplier payment, subscription fee, rent
- utilities, software, equipment, office supplies, travel
- meals, advertising, marketing, hosting, domain
- contractor payment, freelancer, salary, wages, tax

#### Invoice Keywords
- invoice generated, invoice created, invoice sent, billing
- bill client, bill customer, quote, estimate, proposal
- payment request, payment due, accounts receivable

## 4. Inputs

| Input | Source | Description |
|-------|--------|-------------|
| Task content | `Needs_Action/*.md` | Task descriptions with business context |
| MCP actions | MCP servers | External financial actions |
| Direct calls | Python functions | Programmatic accounting entries |
| Ledger files | `Accounting/*.md` | Existing entries for summary generation |

### Example Task Input

```markdown
---
Type: business_task
Status: pending
Priority: high
---
# Task: Process Client Payment

## Description
Payment received from ABC Corp for consulting services.
Amount: $5,000

## Checklist
- [ ] Record payment in accounting
- [ ] Send receipt to client
- [ ] Update invoice status
```

## 5. Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Income entries | `Accounting/income.md` | Recorded income transactions |
| Expense entries | `Accounting/expenses.md` | Recorded expense transactions |
| Invoice entries | `Accounting/invoices.md` | Recorded invoice transactions |
| Weekly summary | `Accounting/weekly_summary.md` | Weekly financial summary with briefing |
| Error log | `Logs/accounting_errors.log` | Accounting error records |

### Entry Format

```markdown
Date: YYYY-MM-DD
Source: Task or MCP Action
Description: Short description
Amount: XXX
Status: Recorded
```

### Ledger Table Format

| Date | Source | Description | Amount | Status |
|------|--------|-------------|--------|--------|
| 2026-02-18 | Task:task_payment_123 | Payment from ABC Corp | $5,000.00 | Recorded |

## 6. Accounting Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ACCOUNTING WORKFLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │  Task/Action │
  │  Detected    │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────┐
  │  Analyze Content │
  │  - Detect type   │
  │  - Extract amount│
  │  - Extract desc  │
  └──────┬───────────┘
         │
    ┌────┴────┐
    │         │
  Business   Not Business
    │         │
    │         ▼
    │    Skip (no action)
    ▼
  ┌──────────────────┐
  │  Determine Type  │
  └──────┬───────────┘
         │
    ┌────┼────┬──────────┐
    │    │    │          │
    ▼    ▼    ▼          ▼
┌────────┐ ┌────────┐ ┌──────────┐
│ INCOME │ │EXPENSE │ │ INVOICE  │
└───┬────┘ └───┬────┘ └────┬─────┘
    │         │           │
    │         │           │
    ▼         ▼           ▼
┌─────────────────────────────────┐
│     Record to Ledger File       │
│  - income.md / expenses.md /    │
│    invoices.md                  │
└─────────────┬───────────────────┘
              │
              ▼
  ┌───────────────────┐
  │  Update Summary   │
  │  - Total amounts  │
  │  - Entry count    │
  │  - Last updated   │
  └─────────┬─────────┘
            │
            ▼
  ┌───────────────────┐
  │  Weekly Summary   │
  │  (Generated       │
  │   automatically)  │
  └───────────────────┘
```

## 7. Integration Rules

### Task Workflow Integration

The accounting skill integrates with the existing task workflow:

```
File Watcher → Task Created → Task Planner → Task Processor → Accounting Skill
                                                              │
                                                              ▼
                                                        Ledger Updated
```

### MCP Server Integration

MCP servers can trigger accounting entries:

```python
# Example: Gmail MCP sends invoice email
from accounting_skill import record_invoice

def send_invoice_email(client_email, amount, description):
    # Send email via MCP
    send_email_via_mcp(...)
    
    # Record in accounting
    record_invoice(description, amount, source="MCP:gmail")
```

### Human Approval Integration

Sensitive accounting actions can require approval:

```
Invoice Generated → Requires Approval → Human Approves → Record Entry
```

## 8. Function Reference

### Core Functions

#### `record_income(description, amount, source, date)`
Record an income entry.

```python
from accounting_skill import record_income

result = record_income(
    description="Consulting services for ABC Corp",
    amount=5000.00,
    source="Task:task_payment_001",
    date="2026-02-18"  # Optional, defaults to today
)
# Returns: {'success': True, 'type': 'income', 'description': ..., 'amount': ...}
```

#### `record_expense(description, amount, source, date)`
Record an expense entry.

```python
from accounting_skill import record_expense

result = record_expense(
    description="Office supplies from Staples",
    amount=150.00,
    source="MCP:expense_tracker"
)
```

#### `record_invoice(description, amount, source, date)`
Record an invoice entry.

```python
from accounting_skill import record_invoice

result = record_invoice(
    description="Invoice #001 for web development",
    amount=2500.00,
    source="Task:task_invoice_001"
)
```

#### `process_business_action(text, source, auto_detect_amount)`
Automatically detect and record business actions from text.

```python
from accounting_skill import process_business_action

text = "Received payment of $5000 from client for consulting"
result = process_business_action(text, source="Task:task_001")
# Automatically detects: income, $5000
```

#### `generate_weekly_summary(week_start, force_update)`
Generate weekly summary with CEO briefing.

```python
from accounting_skill import generate_weekly_summary

result = generate_weekly_summary()
# Returns: {'success': True, 'week_label': '2026-02-17', 
#           'total_income': 5000, 'total_expenses': 150, 
#           'net_profit': 4850, 'briefing': '...'}
```

## 9. Weekly Summary

### Summary Contents

The weekly summary (`Accounting/weekly_summary.md`) includes:

| Section | Content |
|---------|---------|
| **Income Summary** | Total income, transaction count |
| **Expenses Summary** | Total expenses, transaction count |
| **Profit/Loss** | Net profit/loss, profit margin % |
| **Invoices** | Total invoiced, invoice count |
| **CEO Briefing** | Auto-generated business insights |
| **Transaction Details** | Full tables of all transactions |

### CEO Briefing Examples

**Positive Week:**
> **Positive Week:** Net profit of $4,850.00 with 97.0% margin. Generated $5,000.00 across 1 transaction(s). Expenses totaled $150.00 across 1 transaction(s). ✓ Strong profit margin. Consider reinvesting in growth.

**Challenging Week:**
> **Challenging Week:** Net loss of $500.00. Review expenses. Generated $1,000.00 across 2 transaction(s). Expenses totaled $1,500.00 across 3 transaction(s). ⚠ Urgent: Focus on increasing revenue or reducing costs.

### Summary Generation Schedule

| Trigger | Timing |
|---------|--------|
| **Automatic** | Every Monday at 9:00 AM |
| **On-Demand** | Call `generate_weekly_summary()` |
| **Task-Triggered** | After significant transactions |

## 10. Error Handling

### Error Categories

| Category | Examples | Response |
|----------|----------|----------|
| **File Errors** | Ledger file missing, permission denied | Log error, create file if missing |
| **Parse Errors** | Invalid amount format, bad date | Log error, skip entry |
| **Write Errors** | Disk full, file locked | Log error, retry next cycle |

### Error Logging

All errors are logged to `Logs/accounting_errors.log`:

```
[2026-02-18T14:30:00] ACCOUNTING ERROR: Failed to add entry to Accounting/income.md | Context: {'error': 'Permission denied', 'description': 'Payment received', 'amount': 5000}
```

### Workflow Continuity

**Critical Rule:** Accounting errors must NOT stop the workflow.

```python
try:
    record_income(description, amount, source)
except Exception as e:
    log_accounting_error(str(e))
    # Continue with rest of workflow
    # Do NOT raise exception
```

## 11. Safety Rules

| Rule | Enforcement |
|------|-------------|
| **No external dependencies** | All data stored in vault markdown files |
| **No credential storage** | Never store API keys or passwords in ledgers |
| **Append-only entries** | Entries are added, never modified (audit trail) |
| **Error isolation** | Accounting failures don't stop task processing |
| **Transparent logs** | All entries visible in markdown files |
| **Weekly backups** | Copy Accounting/ folder to backup location |

### Data Integrity

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRY INTEGRITY CHECKS                                     │
├─────────────────────────────────────────────────────────────┤
│  ✓ Date format validated (YYYY-MM-DD)                       │
│  ✓ Amount must be numeric                                   │
│  ✓ Description limited to 100 characters                    │
│  ✓ Source tracked for audit trail                           │
│  ✓ Status always set (Recorded, Pending, Completed)         │
└─────────────────────────────────────────────────────────────┘
```

## 12. Example Flows

### Example 1: Payment Received

```
1. Task created: "Process payment from Client X - $3000"
2. Task processor detects business keywords
3. Accounting skill extracts:
   - Type: income
   - Amount: $3000
   - Description: "Payment from Client X"
4. Entry added to Accounting/income.md
5. Weekly summary updated with new total
```

### Example 2: Expense Tracking

```
1. MCP action: Paid for software subscription ($99/month)
2. LinkedIn MCP server triggers accounting entry
3. Entry recorded:
   | Date | Source | Description | Amount | Status |
   |------|--------|-------------|--------|--------|
   | 2026-02-18 | MCP:linkedin | Software subscription | $99.00 | Recorded |
4. Expense total updated
```

### Example 3: Weekly Summary Generation

```
1. Scheduler triggers weekly summary (Monday 9 AM)
2. Accounting skill reads all ledgers
3. Filters entries for current week
4. Calculates totals:
   - Income: $8,000
   - Expenses: $1,200
   - Net: $6,800 (85% margin)
5. Generates CEO briefing
6. Updates Accounting/weekly_summary.md
```

## 13. Folder Structure

```
hackathon-0/
├── Accounting/
│   ├── income.md           # Income ledger
│   ├── expenses.md         # Expenses ledger
│   ├── invoices.md         # Invoices ledger
│   └── weekly_summary.md   # Weekly financial summary
├── Logs/
│   └── accounting_errors.log  # Error log
├── accounting_skill.py     # Accounting module
├── Needs_Action/           # Tasks that may trigger accounting
└── ...
```

## 14. Usage Examples

### Example Task Files

**Income Task:**
```markdown
---
Type: business_task
Status: pending
Priority: high
---
# Task: Record Client Payment

## Description
Payment received from TechCorp Inc. for Q1 consulting services.
Amount: $7,500

## Accounting
- [x] Auto-recorded by accounting skill
```

**Expense Task:**
```markdown
---
Type: business_task
Status: pending
Priority: medium
---
# Task: Pay Software Subscription

## Description
Monthly subscription for development tools.
Paid: $199/month

## Accounting
- [x] Auto-recorded by accounting skill
```

### Python Integration

```python
from accounting_skill import (
    record_income,
    record_expense,
    record_invoice,
    process_business_action,
    generate_weekly_summary
)

# Direct recording
record_income("Website project payment", 5000, "Task:task_001")
record_expense("Server hosting", 50, "MCP:billing")
record_invoice("Invoice #042 - Logo design", 1500, "Task:task_002")

# Auto-detection
text = "Received $2000 payment for consulting work"
process_business_action(text, source="email_integration")

# Weekly summary
summary = generate_weekly_summary()
print(f"Week of {summary['week_label']}")
print(f"Net profit: ${summary['net_profit']:,.2f}")
```

## 15. Related Files

- `Task_Planner_Skill.md` — Task planning that may trigger accounting
- `Human_Approval_Skill.md` — Approval workflow for sensitive transactions
- `Scheduler_Daemon_Trigger_Skill.md` — Scheduled weekly summary generation
- `mcp_servers/README.md` — MCP servers that can trigger accounting
- `Logs/accounting_errors.log` — Error log file

## 16. Quick Reference

### Keyword Detection

| Category | Keywords |
|----------|----------|
| Income | payment received, income, revenue, sale, deposit |
| Expense | expense, payment made, purchase, cost, bill |
| Invoice | invoice generated, invoice sent, billing, quote |

### Function Quick Reference

```python
record_income(desc, amount, source)     # Record income
record_expense(desc, amount, source)    # Record expense
record_invoice(desc, amount, source)    # Record invoice
process_business_action(text, source)   # Auto-detect and record
generate_weekly_summary()               # Generate weekly report
```

### File Locations

| File | Purpose |
|------|---------|
| `Accounting/income.md` | Income ledger |
| `Accounting/expenses.md` | Expense ledger |
| `Accounting/invoices.md` | Invoice ledger |
| `Accounting/weekly_summary.md` | Weekly summary |
| `Logs/accounting_errors.log` | Error log |
