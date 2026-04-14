"""
Finance Watcher — Monitors financial accounts for transactions, balance changes, and alerts.
Creates tasks for unusual activity, large transactions, or scheduled payments.
Supports pluggable backends (API, manual CSV import).

Gold-level features:
- Transaction categorization (operational, marketing, software, salary, infrastructure, misc)
- Subscription detection (recurring payments)
- Anomaly detection (statistical deviation from spending patterns)
- Monthly summary generator
"""

import time
import json
import csv
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log

# State file
STATE_FILE = FOLDERS["logs"] / "finance_state.json"

# Thresholds
LARGE_TRANSACTION_THRESHOLD = 1000.00  # USD — customize
CHECK_INTERVAL = 300  # 5 minutes

# Gold-level: Transaction categories
CATEGORY_KEYWORDS = {
    "operational": ["rent", "utilities", "electric", "water", "internet", "phone", "office", "supplies"],
    "marketing": ["advertising", "ads", "google ads", "facebook ads", "linkedin", "sponsor", "campaign", "promo"],
    "software": ["subscription", "saas", "aws", "azure", "gcp", "cloud", "hosting", "domain", "api", "license", "slack", "notion", "figma", "github", "vercel", "stripe"],
    "salary": ["salary", "payroll", "wages", "contractor", "freelance", "consultant", "bonus", "benefits"],
    "infrastructure": ["server", "hardware", "equipment", "laptop", "monitor", "network", "backup"],
    "finance": ["bank fee", "interest", "loan", "payment", "transfer", "wire", "ach", "swift"],
    "misc": [],  # Catch-all
}

# Subscription detection patterns
SUBSCRIPTION_KEYWORDS = ["subscription", "monthly", "annual", "yearly", "recurring", "renewal"]
SUBSCRIPTION_AMOUNTS = [9.99, 14.99, 19.99, 29.99, 49.99, 99.99, 149.99, 199.99, 299.99, 499.99]


def load_state() -> dict:
    """Load finance watcher state."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "known_transactions": [],
        "last_check": None,
        "last_balance": None,
        # Gold-level state
        "categorized_transactions": {},
        "detected_subscriptions": [],
        "monthly_spending": {},
        "spending_history": [],  # For anomaly detection
    }


def save_state(state: dict):
    """Save finance watcher state."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_bank_api() -> dict:
    """
    Placeholder for bank API integration.
    Replace with actual API call to your bank/financial service.
    Returns: {"balance": float, "transactions": [{"id", "amount", "description", "date", "type"}]}
    """
    api_url = config.bank_api_url
    if not api_url:
        logger.debug("Finance Watcher: No bank API URL configured, skipping API check")
        return {"balance": 0, "transactions": []}

    # TODO: Implement actual bank API integration
    # Example structure:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     resp = await client.get(f"{api_url}/balance", headers={"Authorization": f"Bearer {config.finance_api_key}"})
    #     return resp.json()

    return {"balance": 0, "transactions": []}


def check_csv_import(csv_path: Path) -> list[dict]:
    """Parse transactions from a CSV file."""
    transactions = []
    if not csv_path.exists():
        return transactions

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                transactions.append({
                    "id": row.get("id", row.get("transaction_id", "")),
                    "amount": float(row.get("amount", 0)),
                    "description": row.get("description", row.get("memo", "")),
                    "date": row.get("date", row.get("transaction_date", "")),
                    "type": row.get("type", row.get("transaction_type", "unknown")),
                })
    except Exception as e:
        logger.error(f"Finance Watcher: CSV parse error: {e}")

    return transactions


def is_significant(transaction: dict) -> bool:
    """Determine if a transaction needs attention."""
    amount = abs(transaction.get("amount", 0))

    # Large transactions
    if amount >= LARGE_TRANSACTION_THRESHOLD:
        return True

    # Unusual types
    if transaction.get("type", "").lower() in ["refund", "chargeback", "fee", "interest"]:
        return True

    # Keywords
    description = transaction.get("description", "").lower()
    alert_keywords = ["failed", "declined", "overdraft", "suspicious", "fraud"]
    for kw in alert_keywords:
        if kw in description:
            return True

    # Gold-level: Anomaly detection
    if detect_anomaly(transaction):
        return True

    return False


# ─── Gold-Level Features ───────────────────────────────────────────────


def categorize_transaction(transaction: dict) -> str:
    """
    Categorize a transaction based on description keywords.
    Returns category string: operational, marketing, software, salary, infrastructure, finance, misc
    """
    description = f"{transaction.get('description', '')} {transaction.get('type', '')}".lower()
    vendor = transaction.get("vendor", "").lower()
    combined = f"{description} {vendor}"

    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "misc":
            continue
        for kw in keywords:
            if kw in combined:
                return category

    return "misc"


def detect_subscription(transaction: dict) -> Optional[dict]:
    """
    Detect if a transaction is a subscription payment.
    Returns subscription info dict if detected, None otherwise.
    """
    description = f"{transaction.get('description', '')} {transaction.get('type', '')}".lower()
    amount = abs(transaction.get("amount", 0))

    is_sub = False

    # Check for subscription keywords
    for kw in SUBSCRIPTION_KEYWORDS:
        if kw in description:
            is_sub = True
            break

    # Check for common subscription amounts
    if amount in SUBSCRIPTION_AMOUNTS:
        is_sub = True

    # Check for vendor patterns (e.g. "NETFLIX", "SPOTIFY", "ADOBE")
    known_vendors = [
        "netflix", "spotify", "adobe", "microsoft", "google", "amazon",
        "apple", "github", "vercel", "stripe", "slack", "notion", "figma",
        "zoom", "docusign", "hubspot", "salesforce", "shopify",
    ]
    vendor = transaction.get("vendor", "").lower()
    for v in known_vendors:
        if v in description or v in vendor:
            is_sub = True
            break

    if is_sub:
        # Try to determine frequency
        frequency = "unknown"
        if any(kw in description for kw in ["annual", "yearly", "year"]):
            frequency = "annual"
        elif any(kw in description for kw in ["monthly", "month"]):
            frequency = "monthly"
        elif amount < 50:
            frequency = "monthly"  # Most small recurring are monthly
        else:
            frequency = "monthly"

        return {
            "vendor": vendor or description.split()[0] if description else "unknown",
            "amount": amount,
            "frequency": frequency,
            "description": transaction.get("description", ""),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    return None


def detect_anomaly(transaction: dict) -> bool:
    """
    Detect if a transaction is anomalous based on spending patterns.
    Uses standard deviation from recent spending history.
    """
    state = load_state()
    history = state.get("spending_history", [])

    # Need at least 10 data points for meaningful stats
    if len(history) < 10:
        return False

    amount = abs(transaction.get("amount", 0))

    # Calculate mean and std dev
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    threshold_std = config.finance_anomaly_std_dev
    if std_dev > 0 and amount > mean + (threshold_std * std_dev):
        logger.warning(
            f"Finance Anomaly: ${amount:,.2f} is {threshold_std:.1f}σ above mean ${mean:,.2f}"
        )
        return True

    return False


def record_spending(amount: float):
    """Record a spending amount for anomaly detection history."""
    state = load_state()
    history = state.get("spending_history", [])
    history.append(amount)
    # Keep last 100 entries
    state["spending_history"] = history[-100:]
    save_state(state)


def update_monthly_spending(transaction: dict, category: str):
    """Update monthly spending totals for summary generation."""
    state = load_state()
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")

    if "monthly_spending" not in state:
        state["monthly_spending"] = {}
    if month_key not in state["monthly_spending"]:
        state["monthly_spending"][month_key] = {"total": 0, "by_category": {}, "transactions": 0}

    amount = abs(transaction.get("amount", 0))
    state["monthly_spending"][month_key]["total"] += amount
    state["monthly_spending"][month_key]["transactions"] += 1

    if category not in state["monthly_spending"][month_key]["by_category"]:
        state["monthly_spending"][month_key]["by_category"][category] = 0
    state["monthly_spending"][month_key]["by_category"][category] += amount

    save_state(state)


def detect_subscriptions_in_history() -> list[dict]:
    """Scan known transactions to detect recurring subscriptions."""
    state = load_state()
    detected = state.get("detected_subscriptions", [])

    # If we already have recent detections, return them
    if detected:
        last_detection = max(d.get("detected_at", "2000-01-01") for d in detected)
        last_dt = datetime.fromisoformat(last_detection)
        if (datetime.now(timezone.utc) - last_dt).days < 7:
            return detected

    # Scan for new subscriptions from transaction history
    # This would ideally use actual transaction data; for now use recent state
    new_detected = []
    known_txns = state.get("known_transactions", [])[-50:]  # Last 50

    for txn_id in known_txns:
        # Create synthetic transaction from ID for detection
        txn = {"id": txn_id, "description": txn_id, "amount": 0, "vendor": ""}
        sub = detect_subscription(txn)
        if sub:
            # Check if already detected
            if not any(s["vendor"] == sub["vendor"] for s in detected):
                new_detected.append(sub)
                detected.append(sub)

    state["detected_subscriptions"] = detected
    save_state(state)
    return detected


def generate_monthly_summary(month: str | None = None) -> str:
    """Generate a monthly finance summary markdown file."""
    if month is None:
        month = datetime.now(timezone.utc).strftime("%Y-%m")

    state = load_state()
    monthly_data = state.get("monthly_spending", {}).get(month, {})

    if not monthly_data:
        return f"No data available for {month}."

    summary_file = FOLDERS["content"] / f"Finance_Summary_{month}.md"
    ensure_folders()

    total = monthly_data.get("total", 0)
    txn_count = monthly_data.get("transactions", 0)
    by_category = monthly_data.get("by_category", {})

    content = f"""---
type: finance_summary
month: {month}
generated: {datetime.now(timezone.utc).isoformat()}
---

# 💸 Monthly Finance Summary — {month}

## Overview

| Metric | Value |
|--------|-------|
| Total Spending | ${total:,.2f} |
| Number of Transactions | {txn_count} |
| Average per Transaction | ${total / txn_count:,.2f} |

## Spending by Category

| Category | Amount | % of Total |
|----------|--------|------------|
"""
    for cat, amount in sorted(by_category.items(), key=lambda x: -x[1]):
        pct = (amount / total * 100) if total > 0 else 0
        content += f"| {cat.capitalize()} | ${amount:,.2f} | {pct:.1f}% |\n"

    # Detected subscriptions
    subscriptions = detect_subscriptions_in_history()
    if subscriptions:
        content += f"\n## Detected Subscriptions ({len(subscriptions)})\n\n"
        content += "| Vendor | Amount | Frequency |\n"
        content += "|--------|--------|----------|\n"
        for sub in subscriptions:
            content += f"| {sub['vendor']} | ${sub['amount']:,.2f} | {sub['frequency']} |\n"

        # Monthly subscription cost
        monthly_sub_cost = sum(
            s["amount"] for s in subscriptions if s["frequency"] == "monthly"
        )
        content += f"\n**Monthly Subscription Cost:** ${monthly_sub_cost:,.2f}\n"
        content += f"**Annual Subscription Cost:** ${monthly_sub_cost * 12:,.2f}\n"

    # Comparison with previous month
    prev_month = (datetime.strptime(month, "%Y-%m") - timedelta(days=1)).strftime("%Y-%m")
    prev_data = state.get("monthly_spending", {}).get(prev_month, {})
    prev_total = prev_data.get("total", 0)

    if prev_total > 0:
        change = ((total - prev_total) / prev_total) * 100
        direction = "📈 increased" if change > 0 else "📉 decreased"
        content += f"\n## Month-over-Month\n\n"
        content += f"Spending {direction} by {abs(change):.1f}% compared to {prev_month} (${prev_total:,.2f}).\n"

    content += f"""
---
> Generated by Finance Watcher (Gold Level)
"""
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Finance Monthly Summary generated: {summary_file}")
    return str(summary_file)


def create_finance_task(transaction: dict, reason: str) -> str:
    """Create a task file for a financial event."""
    task_id = f"FINANCE_{transaction['id'][:8].upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    task_file = FOLDERS["inbox"] / f"{task_id}.md"

    amount = transaction.get("amount", 0)
    priority = "high" if abs(amount) >= LARGE_TRANSACTION_THRESHOLD else "normal"
    category = transaction.get("category", "uncategorized")

    # Gold-level: Check for subscription
    sub_info = detect_subscription(transaction)
    sub_note = f"\n> 🔄 **Detected Subscription:** {sub_info['vendor']} — ${sub_info['amount']}/mo ({sub_info['frequency']})" if sub_info else ""

    content = f"""---
task_id: {task_id}
source: finance_watcher
created: {datetime.now(timezone.utc).isoformat()}
status: inbox
priority: {priority}
transaction_id: {transaction['id']}
amount: {amount}
type: {transaction.get('type', 'unknown')}
category: {category}
---

# Task: Financial Event — {reason}

**Source:** Finance Watcher
**Transaction ID:** {transaction['id']}
**Amount:** ${amount:,.2f}
**Category:** {category.capitalize()}
**Type:** {transaction.get('type', 'unknown')}
**Date:** {transaction.get('date', 'Unknown')}
**Description:** {transaction.get('description', 'N/A')}
{sub_note}
## Alert Reason
{reason}

## Action Required
> [!TODO] Review this financial transaction

## Details
- Amount: ${amount:,.2f}
- Category: {category.capitalize()}
- Type: {transaction.get('type', 'unknown')}
- Description: {transaction.get('description', 'N/A')}
- Date: {transaction.get('date', 'Unknown')}
"""
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(content)

    return task_id


def check_finances() -> int:
    """Run one finance check cycle. Returns number of new tasks created."""
    ensure_folders()
    state = load_state()
    tasks_created = 0

    # Check bank API
    api_data = check_bank_api()
    if api_data["balance"] > 0:
        prev_balance = state.get("last_balance")
        if prev_balance is not None and abs(api_data["balance"] - prev_balance) > 0.01:
            logger.info(f"Finance Watcher: Balance changed from ${prev_balance:,.2f} to ${api_data['balance']:,.2f}")

        state["last_balance"] = api_data["balance"]

    # Check CSV import (if exists)
    csv_path = FOLDERS["inbox"] / "finance_import.csv"
    csv_transactions = check_csv_import(csv_path)

    # Combine all transactions
    all_transactions = api_data.get("transactions", []) + csv_transactions

    for txn in all_transactions:
        txn_id = txn.get("id", "")
        if txn_id in state["known_transactions"]:
            continue

        state["known_transactions"].append(txn_id)

        # Gold-level: Categorize the transaction
        category = categorize_transaction(txn)
        txn["category"] = category

        # Gold-level: Update monthly spending
        update_monthly_spending(txn, category)

        # Gold-level: Record spending for anomaly detection
        amount = abs(txn.get("amount", 0))
        if amount > 0:
            record_spending(amount)

        # Gold-level: Check for subscriptions
        sub_info = detect_subscription(txn)
        if sub_info:
            logger.info(f"Finance Watcher: Detected subscription — {sub_info['vendor']} (${sub_info['amount']}/mo)")
            audit_log(
                action="subscription_detected",
                details={"vendor": sub_info["vendor"], "amount": sub_info["amount"], "frequency": sub_info["frequency"]},
            )

        # Check if transaction is significant
        reasons = []
        if abs(txn.get("amount", 0)) >= LARGE_TRANSACTION_THRESHOLD:
            reasons.append(f"Large transaction (>= ${LARGE_TRANSACTION_THRESHOLD:,.2f})")
        if txn.get("type", "").lower() in ["refund", "chargeback", "fee"]:
            reasons.append(f"Unusual type: {txn['type']}")

        # Gold-level: Add category to task
        reasons.append(f"Category: {category}")

        # Create task for significant transactions
        if is_significant(txn):
            reason = "; ".join(reasons) if reasons else "New transaction flagged"
            task_id = create_finance_task(txn, reason)
            audit_log(
                action="finance_transaction_alert",
                task_id=task_id,
                details={"amount": txn.get("amount"), "type": txn.get("type"), "category": category},
            )
            logger.info(f"Finance Watcher: Created task {task_id} for ${txn.get('amount', 0):,.2f} [{category}]")
            tasks_created += 1

    # Prune old transaction IDs
    state["known_transactions"] = state["known_transactions"][-500:]
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    return tasks_created


def run_finance_watcher(interval: int = CHECK_INTERVAL):
    """Run finance watcher in continuous loop."""
    logger.info(f"Finance Watcher started — checking every {interval}s")
    audit_log(action="finance_watcher_started", details={"interval": interval})

    while True:
        try:
            tasks = check_finances()
            if tasks > 0:
                logger.info(f"Finance Watcher: {tasks} new alert(s) this cycle")
        except Exception as e:
            logger.error(f"Finance Watcher error: {e}")
            audit_log(action="finance_watcher_error", level="ERROR", details={"error": str(e)})
        time.sleep(interval)


if __name__ == "__main__":
    run_finance_watcher()
