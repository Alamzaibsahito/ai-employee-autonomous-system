# Odoo MCP Server (JSON-RPC Based)

Enterprise-grade MCP server for Odoo ERP integration using JSON-RPC 2.0 protocol.

## Overview

This server enables the AI Employee to interact with Odoo ERP for:
- Creating customer invoices
- Listing and searching invoices
- Recording payments
- Financial tracking and reporting

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AI Employee    │ ──→ │  Odoo MCP Server │ ──→ │  Odoo ERP       │
│  (Ralph Loop)   │     │  (JSON-RPC 2.0)  │     │  (Local/Self)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Quick Start

### Prerequisites

1. Odoo 19+ installed locally or accessible via network
2. Python 3.8+ with dependencies installed
3. Environment variables configured

### Configuration

Add to `.env` file:

```bash
# ============================================================
# Odoo ERP Configuration (Gold Tier - Enterprise)
# ============================================================
# Odoo server URL (local installation)
ODOO_URL=http://localhost:8069

# Odoo database name
ODOO_DB=odoo_db

# Odoo administrator credentials
ODOO_USERNAME=admin
ODOO_PASSWORD=your_admin_password

# Odoo MCP Server settings
ODOO_MCP_HOST=127.0.0.1
ODOO_MCP_PORT=8003
```

### Starting the Server

**Standalone:**
```bash
cd mcp_servers/odoo_mcp
python server.py
```

**Via startup script:**
```bash
python start_mcp_servers.py
```

**Health check:**
```bash
curl http://127.0.0.1:8003/health
```

## API Endpoints

### JSON-RPC 2.0 Endpoint

The primary endpoint for all Odoo operations:

```bash
POST http://127.0.0.1:8003/jsonrpc
Content-Type: application/json
```

#### Create Invoice

```json
{
  "jsonrpc": "2.0",
  "method": "create_invoice",
  "params": {
    "customer_name": "ABC Corp",
    "amount": 5000.00,
    "description": "Consulting services - Q1 2026"
  },
  "id": "req_001"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": 12345,
    "name": "INV/2026/00001",
    "partner_name": "ABC Corp",
    "amount_total": 5000.00,
    "state": "draft",
    "invoice_date": "2026-02-19"
  },
  "id": "req_001"
}
```

#### List Invoices

```json
{
  "jsonrpc": "2.0",
  "method": "list_invoices",
  "params": {
    "limit": 50
  },
  "id": "req_002"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": [
    {
      "id": 1,
      "name": "INV/2026/00001",
      "partner_name": "ABC Corp",
      "amount_total": 5000.00,
      "state": "posted",
      "invoice_date": "2026-02-15"
    }
  ],
  "id": "req_002"
}
```

#### Record Payment

```json
{
  "jsonrpc": "2.0",
  "method": "record_payment",
  "params": {
    "invoice_id": 12345,
    "amount": 5000.00,
    "payment_date": "2026-02-19",
    "payment_reference": "WIRE_20260219_001"
  },
  "id": "req_003"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": 67890,
    "payment_reference": "PAY/2026/00001",
    "amount": 5000.00,
    "invoice_id": 12345,
    "payment_date": "2026-02-19",
    "state": "posted"
  },
  "id": "req_003"
}
```

### REST-style Endpoints

For simpler integration, REST endpoints are also available:

#### POST /create_invoice

```bash
curl -X POST http://127.0.0.1:8003/create_invoice \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "ABC Corp",
    "amount": 5000.00,
    "description": "Consulting services"
  }'
```

#### POST /list_invoices

```bash
curl -X POST http://127.0.0.1:8003/list_invoices \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```

#### POST /record_payment

```bash
curl -X POST http://127.0.0.1:8003/record_payment \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 12345,
    "amount": 5000.00,
    "payment_date": "2026-02-19"
  }'
```

## Integration with AI Employee

### Python Client Example

```python
import requests

class OdooClient:
    """Client for Odoo MCP Server."""
    
    def __init__(self, base_url="http://127.0.0.1:8003"):
        self.base_url = base_url
    
    def create_invoice(self, customer_name: str, amount: float, description: str) -> dict:
        """Create an invoice in Odoo."""
        response = requests.post(
            f"{self.base_url}/create_invoice",
            json={
                "customer_name": customer_name,
                "amount": amount,
                "description": description
            }
        )
        return response.json()
    
    def list_invoices(self, limit: int = 50) -> list:
        """List invoices from Odoo."""
        response = requests.post(
            f"{self.base_url}/list_invoices",
            json={"limit": limit}
        )
        data = response.json()
        return data.get("invoices", [])
    
    def record_payment(self, invoice_id: int, amount: float, payment_date: str = None) -> dict:
        """Record a payment for an invoice."""
        response = requests.post(
            f"{self.base_url}/record_payment",
            json={
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_date": payment_date
            }
        )
        return response.json()


# Usage
odoo = OdooClient()

# Create invoice
result = odoo.create_invoice("Client X", 5000.00, "Web development services")
print(f"Invoice created: {result['invoice_id']}")

# List invoices
invoices = odoo.list_invoices()
print(f"Total invoices: {len(invoices)}")

# Record payment
payment = odoo.record_payment(result['invoice_id'], 5000.00)
print(f"Payment recorded: {payment['payment_id']}")
```

### Integration with Accounting Skill

The Odoo MCP server integrates with the existing `accounting_skill.py`:

```python
from accounting_skill import record_invoice
import requests

def sync_with_odoo(description: str, amount: float, customer: str):
    """Sync accounting entry with Odoo."""
    
    # Record in vault-based accounting
    vault_result = record_invoice(description, amount, "Odoo Sync")
    
    # Sync with Odoo
    odoo_response = requests.post(
        "http://127.0.0.1:8003/create_invoice",
        json={
            "customer_name": customer,
            "amount": amount,
            "description": description
        }
    )
    
    return {
        "vault": vault_result,
        "odoo": odoo_response.json()
    }
```

## Error Handling

### Graceful Degradation

The server is designed to never crash the Ralph loop:

- Missing credentials → Returns error response, doesn't crash
- Network timeout → Logs error, returns graceful failure
- Odoo unavailable → Returns structured error with retry info

### Error Response Format

```json
{
  "success": false,
  "error": "Odoo credentials not configured",
  "error_code": "CREDENTIALS_NOT_CONFIGURED",
  "details": {
    "missing_vars": ["ODOO_URL", "ODOO_DB"]
  }
}
```

### Common Error Codes

| Error Code | Description | Retry? |
|------------|-------------|--------|
| `CREDENTIALS_NOT_CONFIGURED` | Missing environment variables | No |
| `CONNECTION_TIMEOUT` | Odoo server not responding | Yes |
| `AUTHENTICATION_FAILED` | Invalid Odoo credentials | No |
| `INVOICE_NOT_FOUND` | Invoice ID doesn't exist | No |
| `INTERNAL_ERROR` | Server error | Yes |

## Logging

All actions are logged to:

1. **System Log:** `Logs/System_Log.md`
2. **Action Log:** Via `action_logger` module
3. **Console:** Standard logging output

### Log Entry Format

```
[2026-02-19T10:30:00] ODOO_MCP | create_invoice | success | {"invoice_id": 12345, "customer": "ABC Corp"}
```

## Production Deployment

### Odoo 19+ JSON-RPC API

For production, replace the simulated responses with actual Odoo API calls:

```python
def _make_jsonrpc_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Make actual JSON-RPC call to Odoo."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": params.get("id")
    }
    
    response = requests.post(
        f"{self.config.url}/jsonrpc",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()
```

### Odoo Model Reference

| Operation | Odoo Model | Method |
|-----------|------------|--------|
| Create Invoice | `account.move` | `create()` |
| List Invoices | `account.move` | `search_read()` |
| Record Payment | `account.payment.register` | `create()` |

## Security Notes

- **Never commit credentials** - Use environment variables
- **Bind to localhost** - Default is `127.0.0.1`
- **Use HTTPS in production** - For remote Odoo servers
- **Rotate passwords regularly** - Especially for admin accounts
- **Audit logs regularly** - Review `Logs/System_Log.md`

## Related Files

- `accounting_skill.py` - Vault-based accounting integration
- `mcp_servers/gmail_mcp/server.py` - Similar MCP server pattern
- `mcp_servers/linkedin_mcp/server.py` - Similar MCP server pattern
- `skills/error_recovery.py` - Error handling integration
- `Logs/System_Log.md` - Audit trail

## Troubleshooting

### Server Won't Start

1. Check if port 8003 is in use
2. Verify `.env` file exists
3. Check Python dependencies installed

### Credentials Error

1. Verify all ODOO_* variables in `.env`
2. Test Odoo connection manually
3. Check Odoo server is running

### JSON-RPC Errors

1. Verify method name is correct
2. Check params structure matches schema
3. Review `Logs/System_Log.md` for details
