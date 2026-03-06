"""
Accounting Skill Module

A lightweight vault-based accounting system that automatically tracks
business-related actions by updating markdown ledger files.

This module:
- Detects business actions (income, expenses, invoices)
- Records entries to appropriate ledger files
- Generates weekly summaries with CEO briefings
- Logs errors without breaking the workflow

Integration: Call these functions from agent skills or MCP actions.
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Error log file
ERROR_LOG_PATH = "Logs/accounting_errors.log"

# Accounting folder and files
ACCOUNTING_FOLDER = "Accounting"
INCOME_FILE = os.path.join(ACCOUNTING_FOLDER, "income.md")
EXPENSES_FILE = os.path.join(ACCOUNTING_FOLDER, "expenses.md")
INVOICES_FILE = os.path.join(ACCOUNTING_FOLDER, "invoices.md")
WEEKLY_SUMMARY_FILE = os.path.join(ACCOUNTING_FOLDER, "weekly_summary.md")


# ============================================================
# Error Logging
# ============================================================

def log_accounting_error(error: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an accounting error to the error log file.
    
    Args:
        error: Error message
        context: Optional context dictionary with additional details
    """
    timestamp = datetime.now().isoformat()
    
    # Ensure Logs directory exists
    os.makedirs("Logs", exist_ok=True)
    
    # Format error entry
    error_entry = f"[{timestamp}] ACCOUNTING ERROR: {error}"
    if context:
        error_entry += f" | Context: {context}"
    error_entry += "\n"
    
    # Append to error log
    try:
        with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(error_entry)
    except Exception as e:
        logger.error(f"Failed to write to error log: {e}")
    
    logger.error(f"Accounting error logged: {error}")


# ============================================================
# Business Action Detection
# ============================================================

# Keywords that indicate business-related actions
INCOME_KEYWORDS = [
    'payment received', 'income', 'revenue', 'sale', 'invoice paid',
    'client payment', 'customer payment', 'deposit', 'refund received',
    'subscription', 'service fee', 'consulting fee', 'project payment',
    'milestone payment', 'retainer', 'commission', 'royalty',
    'money received', 'funds received', 'transfer received'
]

EXPENSE_KEYWORDS = [
    'expense', 'payment made', 'purchase', 'cost', 'bill', 'invoice',
    'vendor payment', 'supplier payment', 'subscription fee', 'rent',
    'utilities', 'software', 'equipment', 'office supplies', 'travel',
    'meals', 'advertising', 'marketing', 'hosting', 'domain',
    'contractor payment', 'freelancer', 'salary', 'wages', 'tax',
    'insurance', 'loan payment', 'interest', 'bank fee', 'transaction fee',
    'money sent', 'funds transferred', 'paid for'
]

INVOICE_KEYWORDS = [
    'invoice generated', 'invoice created', 'invoice sent', 'billing',
    'bill client', 'bill customer', 'quote', 'estimate', 'proposal',
    'payment request', 'payment due', 'accounts receivable'
]


def detect_action_type(text: str) -> Optional[str]:
    """
    Detect the type of business action from text.
    
    Args:
        text: Text to analyze (task description, content, etc.)
    
    Returns:
        'income', 'expense', 'invoice', or None
    """
    text_lower = text.lower()
    
    # Check for invoice first (higher priority)
    for keyword in INVOICE_KEYWORDS:
        if keyword in text_lower:
            return 'invoice'
    
    # Check for income
    for keyword in INCOME_KEYWORDS:
        if keyword in text_lower:
            return 'income'
    
    # Check for expenses
    for keyword in EXPENSE_KEYWORDS:
        if keyword in text_lower:
            return 'expense'
    
    return None


def extract_amount(text: str) -> Optional[float]:
    """
    Extract monetary amount from text.
    
    Args:
        text: Text that may contain a monetary amount
    
    Returns:
        Amount as float, or None if not found
    """
    # Pattern for $XXX.XX or XXX.XX
    patterns = [
        r'\$(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)',  # $1,000.00 (with commas)
        r'\$(\d+\.?\d*)',  # $100 or $100.00 or $5000
        r'(\d{1,3}(?:,\d{3})+(?:\.\d{2})?)\s*(?:dollars?|USD|usd)',  # 1,000 dollars
        r'(\d+\.?\d*)\s*(?:dollars?|USD|usd)',  # 100 dollars
        r'amount[:\s]+\$?(\d+\.?\d*)',  # amount: $100
        r'price[:\s]+\$?(\d+\.?\d*)',  # price: $100
        r'cost[:\s]+\$?(\d+\.?\d*)',  # cost: $100
        r'total[:\s]+\$?(\d+\.?\d*)',  # total: $100
        r'received[:\s]+\$?(\d+\.?\d*)',  # received: $100
        r'paid[:\s]+\$?(\d+\.?\d*)',  # paid: $100
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                return float(amount_str)
            except ValueError:
                continue
    
    return None


def extract_description(text: str, action_type: str) -> str:
    """
    Extract or generate a short description from text.
    
    Args:
        text: Source text
        action_type: Type of action (income, expense, invoice)
    
    Returns:
        Short description string
    """
    # Try to get first line or sentence
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line and len(line) > 10 and len(line) < 200:
            # Remove markdown formatting
            line = re.sub(r'[#*\[\]]', '', line).strip()
            return line[:100]  # Limit to 100 chars
    
    # Fallback description
    return f"{action_type.capitalize()} transaction"


# ============================================================
# Ledger Operations
# ============================================================

def ensure_accounting_files_exist() -> None:
    """Ensure all accounting files and folders exist."""
    os.makedirs(ACCOUNTING_FOLDER, exist_ok=True)
    
    files = [INCOME_FILE, EXPENSES_FILE, INVOICES_FILE, WEEKLY_SUMMARY_FILE]
    for file_path in files:
        if not os.path.exists(file_path):
            logger.warning(f"Accounting file missing: {file_path}")


def read_ledger_entries(file_path: str) -> List[Dict[str, Any]]:
    """
    Read entries from a ledger file.
    
    Args:
        file_path: Path to the ledger markdown file
    
    Returns:
        List of entry dictionaries
    """
    entries = []
    
    if not os.path.exists(file_path):
        return entries
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse entries from the table format
        # Looking for pattern: | Date | Source | Description | Amount | Status |
        lines = content.split('\n')
        in_table = False
        
        for line in lines:
            line = line.strip()
            
            # Detect table start
            if '| Date |' in line or '|------|' in line:
                in_table = True
                continue
            
            # Detect table end
            if in_table and line.startswith('---'):
                break
            
            # Parse table row
            if in_table and line.startswith('|') and line.endswith('|'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 5 and parts[0] != 'Date':
                    try:
                        amount_str = parts[3].replace('$', '').replace(',', '')
                        entries.append({
                            'date': parts[0],
                            'source': parts[1],
                            'description': parts[2],
                            'amount': float(amount_str) if amount_str else 0.0,
                            'status': parts[4]
                        })
                    except (ValueError, IndexError):
                        continue
    
    except Exception as e:
        log_accounting_error(f"Failed to read ledger {file_path}", {'error': str(e)})
    
    return entries


def add_ledger_entry(
    file_path: str,
    date: str,
    source: str,
    description: str,
    amount: float,
    status: str = "Recorded"
) -> bool:
    """
    Add an entry to a ledger file.
    
    Args:
        file_path: Path to the ledger markdown file
        date: Date string (YYYY-MM-DD)
        source: Source of the entry (Task, MCP Action, etc.)
        description: Short description
        amount: Monetary amount
        status: Entry status
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Ledger file not found: {file_path}")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create new entry row
        new_row = f"| {date} | {source} | {description} | ${amount:.2f} | {status} |"
        
        # Find the table and insert after the header
        lines = content.split('\n')
        new_lines = []
        inserted = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Insert after the separator line (|------|...)
            if not inserted and '|------|' in line and '|' in line:
                new_lines.append(new_row)
                inserted = True
        
        if not inserted:
            # If no table found, append to end
            new_lines.append("\n## Recent Entries\n")
            new_lines.append("| Date | Source | Description | Amount | Status |")
            new_lines.append("|------|--------|-------------|--------|--------|")
            new_lines.append(new_row)
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        # Update summary
        update_ledger_summary(file_path)
        
        logger.info(f"Added entry to {file_path}: {description} - ${amount:.2f}")
        return True
    
    except Exception as e:
        log_accounting_error(f"Failed to add entry to {file_path}", {
            'error': str(e),
            'description': description,
            'amount': amount
        })
        return False


def update_ledger_summary(file_path: str) -> None:
    """
    Update the summary section of a ledger file.
    
    Args:
        file_path: Path to the ledger markdown file
    """
    try:
        entries = read_ledger_entries(file_path)
        total = sum(entry['amount'] for entry in entries)
        count = len(entries)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine category for summary label
        if 'income' in file_path.lower():
            label = "Total Income"
        elif 'expenses' in file_path.lower():
            label = "Total Expenses"
        elif 'invoices' in file_path.lower():
            label = "Total Invoiced"
        else:
            label = "Total"
        
        # Update summary section
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Find and replace summary section
        summary_pattern = rf'- \*\*{label}:\*\* \$[\d,]+\.?\d*'
        summary_replacement = f"- **{label}:** ${total:,.2f}"
        content = re.sub(summary_pattern, summary_replacement, content)
        
        # Update entries count
        count_pattern = r'- \*\*Entries Count:\*\* \d+'
        count_replacement = f"- **Entries Count:** {count}"
        content = re.sub(count_pattern, count_replacement, content)
        
        # Update last updated
        updated_pattern = r'- \*\*Last Updated:\*\* .*'
        updated_replacement = f"- **Last Updated:** {timestamp}"
        content = re.sub(updated_pattern, updated_replacement, content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    except Exception as e:
        log_accounting_error(f"Failed to update summary for {file_path}", {'error': str(e)})


# ============================================================
# Main Accounting Functions
# ============================================================

def record_income(
    description: str,
    amount: float,
    source: str = "Task",
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an income entry.
    
    Args:
        description: Description of the income
        amount: Amount received
        source: Source of the record (Task, MCP Action, etc.)
        date: Date string (YYYY-MM-DD), defaults to today
    
    Returns:
        Dictionary with success status and details
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    success = add_ledger_entry(
        file_path=INCOME_FILE,
        date=date,
        source=source,
        description=description[:100],
        amount=amount,
        status="Recorded"
    )
    
    return {
        'success': success,
        'type': 'income',
        'description': description,
        'amount': amount,
        'date': date,
        'source': source
    }


def record_expense(
    description: str,
    amount: float,
    source: str = "Task",
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an expense entry.
    
    Args:
        description: Description of the expense
        amount: Amount spent
        source: Source of the record (Task, MCP Action, etc.)
        date: Date string (YYYY-MM-DD), defaults to today
    
    Returns:
        Dictionary with success status and details
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    success = add_ledger_entry(
        file_path=EXPENSES_FILE,
        date=date,
        source=source,
        description=description[:100],
        amount=amount,
        status="Recorded"
    )
    
    return {
        'success': success,
        'type': 'expense',
        'description': description,
        'amount': amount,
        'date': date,
        'source': source
    }


def record_invoice(
    description: str,
    amount: float,
    source: str = "Task",
    date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an invoice entry.
    
    Args:
        description: Description of the invoice
        amount: Invoice amount
        source: Source of the record (Task, MCP Action, etc.)
        date: Date string (YYYY-MM-DD), defaults to today
    
    Returns:
        Dictionary with success status and details
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    success = add_ledger_entry(
        file_path=INVOICES_FILE,
        date=date,
        source=source,
        description=description[:100],
        amount=amount,
        status="Recorded"
    )
    
    return {
        'success': success,
        'type': 'invoice',
        'description': description,
        'amount': amount,
        'date': date,
        'source': source
    }


def process_business_action(
    text: str,
    source: str = "Task",
    auto_detect_amount: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Process text to detect and record business actions automatically.
    
    Args:
        text: Text to analyze (task description, content, etc.)
        source: Source of the action (Task, MCP Action, etc.)
        auto_detect_amount: Whether to auto-extract amount from text
    
    Returns:
        Dictionary with action details if business action detected, None otherwise
    """
    # Detect action type
    action_type = detect_action_type(text)
    
    if action_type is None:
        return None
    
    # Extract amount if requested
    amount = 0.0
    if auto_detect_amount:
        amount = extract_amount(text)
    
    # Extract description
    description = extract_description(text, action_type)
    
    # Record the action
    if action_type == 'income':
        result = record_income(description, amount if amount > 0 else 0.0, source)
    elif action_type == 'expense':
        result = record_expense(description, amount if amount > 0 else 0.0, source)
    elif action_type == 'invoice':
        result = record_invoice(description, amount if amount > 0 else 0.0, source)
    else:
        return None
    
    return result


# ============================================================
# Weekly Summary Generation
# ============================================================

def get_week_start(date: Optional[datetime] = None) -> datetime:
    """Get the Monday of the week for a given date."""
    if date is None:
        date = datetime.now()
    return date - timedelta(days=date.weekday())


def generate_weekly_summary(
    week_start: Optional[datetime] = None,
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Generate or update the weekly accounting summary.
    
    Args:
        week_start: Start of the week (Monday), defaults to current week
        force_update: Force regeneration even if summary exists
    
    Returns:
        Dictionary with summary data
    """
    if week_start is None:
        week_start = get_week_start()
    
    week_end = week_start + timedelta(days=6)
    week_label = week_start.strftime('%Y-%m-%d')
    
    try:
        # Read all ledger entries
        income_entries = read_ledger_entries(INCOME_FILE)
        expense_entries = read_ledger_entries(EXPENSES_FILE)
        invoice_entries = read_ledger_entries(INVOICES_FILE)
        
        # Filter entries for this week
        def filter_week_entries(entries: List[Dict]) -> List[Dict]:
            filtered = []
            for entry in entries:
                try:
                    entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
                    if week_start <= entry_date <= week_end:
                        filtered.append(entry)
                except ValueError:
                    continue
            return filtered
        
        weekly_income = filter_week_entries(income_entries)
        weekly_expenses = filter_week_entries(expense_entries)
        weekly_invoices = filter_week_entries(invoice_entries)
        
        # Calculate totals
        total_income = sum(e['amount'] for e in weekly_income)
        total_expenses = sum(e['amount'] for e in weekly_expenses)
        total_invoiced = sum(e['amount'] for e in weekly_invoices)
        net_profit = total_income - total_expenses
        profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        
        # Generate CEO briefing
        briefing = generate_ceo_briefing(
            total_income=total_income,
            total_expenses=total_expenses,
            net_profit=net_profit,
            profit_margin=profit_margin,
            income_count=len(weekly_income),
            expense_count=len(weekly_expenses)
        )
        
        # Update weekly summary file
        update_weekly_summary_file(
            week_label=week_label,
            week_start=week_start,
            week_end=week_end,
            total_income=total_income,
            total_expenses=total_expenses,
            net_profit=net_profit,
            profit_margin=profit_margin,
            total_invoiced=total_invoiced,
            briefing=briefing,
            income_entries=weekly_income,
            expense_entries=weekly_expenses,
            invoice_entries=weekly_invoices
        )
        
        logger.info(f"Generated weekly summary for week of {week_label}")
        
        return {
            'success': True,
            'week_label': week_label,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': profit_margin,
            'total_invoiced': total_invoiced,
            'briefing': briefing
        }
    
    except Exception as e:
        log_accounting_error("Failed to generate weekly summary", {'error': str(e)})
        return {
            'success': False,
            'error': str(e)
        }


def generate_ceo_briefing(
    total_income: float,
    total_expenses: float,
    net_profit: float,
    profit_margin: float,
    income_count: int,
    expense_count: int
) -> str:
    """
    Generate a short CEO briefing based on financial data.
    
    Args:
        total_income: Total income for the period
        total_expenses: Total expenses for the period
        net_profit: Net profit (income - expenses)
        profit_margin: Profit margin percentage
        income_count: Number of income transactions
        expense_count: Number of expense transactions
    
    Returns:
        Briefing text
    """
    lines = []
    
    # Overall performance
    if net_profit > 0:
        lines.append(f"**Positive Week:** Net profit of ${net_profit:,.2f} with {profit_margin:.1f}% margin.")
    elif net_profit < 0:
        lines.append(f"**Challenging Week:** Net loss of ${abs(net_profit):,.2f}. Review expenses.")
    else:
        lines.append("**Break-even Week:** Income matched expenses.")
    
    # Income highlights
    if income_count > 0:
        lines.append(f"Generated ${total_income:,.2f} across {income_count} transaction(s).")
    else:
        lines.append("No income transactions recorded this week.")
    
    # Expense highlights
    if expense_count > 0:
        lines.append(f"Expenses totaled ${total_expenses:,.2f} across {expense_count} transaction(s).")
    else:
        lines.append("No expenses recorded this week.")
    
    # Recommendation
    if profit_margin > 30:
        lines.append("[OK] Strong profit margin. Consider reinvesting in growth.")
    elif profit_margin > 15:
        lines.append("[OK] Healthy margin. Monitor for optimization opportunities.")
    elif profit_margin > 0:
        lines.append("[!] Low margin. Review pricing and cost structure.")
    else:
        lines.append("[!] Urgent: Focus on increasing revenue or reducing costs.")
    
    return " ".join(lines)


def update_weekly_summary_file(
    week_label: str,
    week_start: datetime,
    week_end: datetime,
    total_income: float,
    total_expenses: float,
    net_profit: float,
    profit_margin: float,
    total_invoiced: float,
    briefing: str,
    income_entries: List[Dict],
    expense_entries: List[Dict],
    invoice_entries: List[Dict]
) -> None:
    """
    Update the weekly summary markdown file.
    
    Args:
        week_label: Week label string
        week_start: Start date of the week
        week_end: End date of the week
        total_income: Total income
        total_expenses: Total expenses
        net_profit: Net profit
        profit_margin: Profit margin percentage
        total_invoiced: Total invoiced
        briefing: CEO briefing text
        income_entries: List of income entries
        expense_entries: List of expense entries
        invoice_entries: List of invoice entries
    """
    try:
        # Generate content
        content = f'''---
Type: accounting_summary
Category: weekly_report
Status: active
Created_at: {datetime.now().strftime('%Y-%m-%d')}
Week_start: {week_start.strftime('%Y-%m-%d')}
Week_end: {week_end.strftime('%Y-%m-%d')}
---

# Weekly Accounting Summary

## Purpose
Automatically generated weekly summary of business financial activity.

---

## Week of: {week_label}

### Income Summary
- **Total Income:** ${total_income:,.2f}
- **Number of Transactions:** {len(income_entries)}

### Expenses Summary
- **Total Expenses:** ${total_expenses:,.2f}
- **Number of Transactions:** {len(expense_entries)}

### Profit/Loss
- **Net Profit/Loss:** ${net_profit:,.2f}
- **Profit Margin:** {profit_margin:.1f}%

### Invoices
- **Total Invoiced:** ${total_invoiced:,.2f}
- **Number of Invoices:** {len(invoice_entries)}

---

## CEO Briefing

> {briefing}

---

## Transaction Details

### Income Transactions
| Date | Description | Amount |
|------|-------------|--------|
'''
        
        if income_entries:
            for entry in income_entries:
                content += f"| {entry['date']} | {entry['description']} | ${entry['amount']:.2f} |\n"
        else:
            content += "| - | No transactions | - |\n"
        
        content += "\n### Expense Transactions\n| Date | Description | Amount |\n|------|-------------|--------|\n"
        
        if expense_entries:
            for entry in expense_entries:
                content += f"| {entry['date']} | {entry['description']} | ${entry['amount']:.2f} |\n"
        else:
            content += "| - | No transactions | - |\n"
        
        content += "\n### Invoices\n| Date | Description | Amount |\n|------|-------------|--------|\n"
        
        if invoice_entries:
            for entry in invoice_entries:
                content += f"| {entry['date']} | {entry['description']} | ${entry['amount']:.2f} |\n"
        else:
            content += "| - | No transactions | - |\n"
        
        content += "\n---\n\n*Generated automatically by Accounting Skill*\n"
        
        # Write to file
        with open(WEEKLY_SUMMARY_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
    
    except Exception as e:
        log_accounting_error("Failed to update weekly summary file", {'error': str(e)})


# ============================================================
# Task Integration
# ============================================================

def process_task_for_accounting(task_content: str, task_file: str) -> Optional[Dict[str, Any]]:
    """
    Process a task file for accounting entries.
    
    Args:
        task_content: Full content of the task file
        task_file: Name of the task file
    
    Returns:
        Dictionary with action details if business action detected, None otherwise
    """
    # Process the task content
    result = process_business_action(
        text=task_content,
        source=f"Task:{task_file}",
        auto_detect_amount=True
    )
    
    if result:
        logger.info(f"Accounting entry recorded from task {task_file}")
    
    return result


# ============================================================
# Initialization
# ============================================================

def initialize_accounting() -> None:
    """Initialize the accounting system by ensuring files exist."""
    ensure_accounting_files_exist()
    logger.info("Accounting system initialized")


# Auto-initialize on import
initialize_accounting()


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    print("Accounting Skill Module")
    print("=" * 40)
    
    # Test detection
    test_texts = [
        "Payment received from client for $5000",
        "Paid for office supplies $150",
        "Invoice generated for consulting services $2500",
        "Regular task with no business action"
    ]
    
    print("\nTesting business action detection:")
    for text in test_texts:
        action_type = detect_action_type(text)
        amount = extract_amount(text)
        print(f"  Text: {text[:50]}...")
        print(f"    Action: {action_type}, Amount: ${amount if amount else 'N/A'}")
    
    print("\nGenerating weekly summary...")
    result = generate_weekly_summary()
    print(f"  Success: {result.get('success', False)}")
    if result.get('success'):
        print(f"  Week: {result['week_label']}")
        print(f"  Income: ${result['total_income']:,.2f}")
        print(f"  Expenses: ${result['total_expenses']:,.2f}")
        print(f"  Net: ${result['net_profit']:,.2f}")
