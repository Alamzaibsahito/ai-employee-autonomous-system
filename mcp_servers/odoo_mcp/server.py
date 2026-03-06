"""
Odoo MCP Server (JSON-RPC Based)

Provides Model Context Protocol (MCP) server for Odoo ERP integration via JSON-RPC.
This server enables the AI Employee to interact with Odoo for:
- Creating invoices
- Listing invoices
- Recording payments

Architecture:
- JSON-RPC 2.0 structure (simulated for production readiness)
- Environment variable based configuration
- Graceful error handling (never crashes Ralph loop)
- Comprehensive logging to Logs/System_Log.md

Usage:
    python mcp_servers/odoo_mcp/server.py

Or via startup script:
    python start_mcp_servers.py
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.auth import (
    get_credential_manager,
    create_action_logger,
    CredentialManager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Odoo MCP Server",
    description="MCP server for Odoo ERP integration via JSON-RPC",
    version="1.0.0"
)

# Initialize components
credential_manager = get_credential_manager()
action_logger = create_action_logger("odoo")

# System log file for audit trail
SYSTEM_LOG_PATH = "Logs/System_Log.md"


# ============================================================
# Environment Configuration
# ============================================================

class OdooConfig:
    """Odoo configuration from environment variables."""
    
    def __init__(self):
        self.url = os.getenv("ODOO_URL", "http://localhost:8069")
        self.db = os.getenv("ODOO_DB", "odoo_db")
        self.username = os.getenv("ODOO_USERNAME", "admin")
        self.password = os.getenv("ODOO_PASSWORD", "admin")
        self.uid: Optional[int] = None
    
    def is_configured(self) -> bool:
        """Check if all required config is present."""
        return all([
            self.url,
            self.db,
            self.username,
            self.password
        ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Return config as dictionary."""
        return {
            "url": self.url,
            "db": self.db,
            "username": self.username,
            "password": self.password
        }


odoo_config = OdooConfig()


# ============================================================
# JSON-RPC Request/Response Models
# ============================================================

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request model."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response model."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


# ============================================================
# Odoo ERP Request/Response Models
# ============================================================

class CreateInvoiceRequest(BaseModel):
    """Request model for creating an invoice."""
    customer_name: str = Field(..., description="Customer name")
    amount: float = Field(..., gt=0, description="Invoice amount")
    description: str = Field(..., description="Invoice description")
    invoice_type: str = Field(default="out_invoice", description="Invoice type (out_invoice/in_invoice)")


class RecordPaymentRequest(BaseModel):
    """Request model for recording a payment."""
    invoice_id: int = Field(..., description="Invoice ID to pay")
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_date: Optional[str] = Field(None, description="Payment date (YYYY-MM-DD)")
    payment_reference: Optional[str] = Field(None, description="Payment reference")


class InvoiceResponse(BaseModel):
    """Response model for invoice operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    invoice_id: Optional[int] = None


class ListInvoicesResponse(BaseModel):
    """Response model for listing invoices."""
    success: bool
    message: str
    invoices: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class PaymentResponse(BaseModel):
    """Response model for payment operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    payment_id: Optional[int] = None


# ============================================================
# System Logging
# ============================================================

def log_to_system_log(action: str, status: str, details: Dict[str, Any]) -> None:
    """
    Log an action to the system log file.
    
    Args:
        action: Action performed
        status: Status (success/error/pending)
        details: Additional details
    """
    try:
        os.makedirs("Logs", exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        log_entry = f"[{timestamp}] ODOO_MCP | {action} | {status} | {json.dumps(details)}\n"
        
        with open(SYSTEM_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    except Exception as e:
        logger.error(f"Failed to write to system log: {e}")


# ============================================================
# Odoo JSON-RPC Client
# ============================================================

class OdooJSONRPCClient:
    """
    Odoo JSON-RPC client for ERP operations.
    
    This client simulates production-ready JSON-RPC calls to Odoo.
    In production, replace simulate_* methods with actual API calls.
    """
    
    def __init__(self, config: OdooConfig):
        self.config = config
        self.session = requests.Session()
        self.base_url = f"{config.url}/jsonrpc"
    
    def _make_jsonrpc_call(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make a JSON-RPC call to Odoo.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            timeout: Request timeout in seconds
            
        Returns:
            JSON-RPC response
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": f"req_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            # In production, this would be an actual HTTP call:
            # response = self.session.post(self.base_url, json=payload, headers=headers, timeout=timeout)
            # response.raise_for_status()
            # return response.json()
            
            # For now, simulate the response
            return self._simulate_odoo_response(method, params)
            
        except requests.exceptions.Timeout:
            raise Exception("Odoo JSON-RPC call timed out")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Odoo JSON-RPC call failed: {str(e)}")
    
    def _simulate_odoo_response(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate Odoo JSON-RPC response for testing.
        
        In production, remove this and use actual API calls.
        """
        # Simulate authentication
        if not self.config.is_configured():
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": "Odoo credentials not configured",
                    "data": "Missing environment variables"
                },
                "id": params.get("id")
            }
        
        # Simulate different methods
        if "account.move.create" in method or "create_invoice" in method:
            invoice_id = int(datetime.now().timestamp()) % 100000
            return {
                "jsonrpc": "2.0",
                "result": {
                    "id": invoice_id,
                    "name": f"INV/{datetime.now().strftime('%Y')}/{invoice_id:05d}",
                    "partner_name": params.get("partner_name", "Customer"),
                    "amount_total": params.get("amount", 0),
                    "state": "draft",
                    "invoice_date": datetime.now().strftime('%Y-%m-%d')
                },
                "id": params.get("id")
            }
        
        elif "account.move.search_read" in method or "list_invoices" in method:
            # Return simulated invoices
            return {
                "jsonrpc": "2.0",
                "result": [
                    {
                        "id": 1,
                        "name": f"INV/{datetime.now().strftime('%Y')}/00001",
                        "partner_name": "ABC Corp",
                        "amount_total": 5000.00,
                        "state": "posted",
                        "invoice_date": "2026-02-15"
                    },
                    {
                        "id": 2,
                        "name": f"INV/{datetime.now().strftime('%Y')}/00002",
                        "partner_name": "XYZ Inc",
                        "amount_total": 2500.00,
                        "state": "draft",
                        "invoice_date": "2026-02-17"
                    }
                ],
                "id": params.get("id")
            }
        
        elif "account.payment.register.create" in method or "record_payment" in method:
            payment_id = int(datetime.now().timestamp()) % 100000
            return {
                "jsonrpc": "2.0",
                "result": {
                    "id": payment_id,
                    "payment_reference": f"PAY/{datetime.now().strftime('%Y')}/{payment_id:05d}",
                    "amount": params.get("amount", 0),
                    "invoice_id": params.get("invoice_id"),
                    "payment_date": datetime.now().strftime('%Y-%m-%d'),
                    "state": "posted"
                },
                "id": params.get("id")
            }
        
        elif "authenticate" in method:
            return {
                "jsonrpc": "2.0",
                "result": {
                    "uid": 2,
                    "username": self.config.username,
                    "name": "Administrator"
                },
                "id": params.get("id")
            }
        
        return {
            "jsonrpc": "2.0",
            "result": {},
            "id": params.get("id")
        }
    
    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Odoo."""
        return self._make_jsonrpc_call(
            "authenticate",
            {
                "db": self.config.db,
                "login": self.config.username,
                "password": self.config.password
            }
        )
    
    def create_invoice(
        self,
        customer_name: str,
        amount: float,
        description: str,
        invoice_type: str = "out_invoice"
    ) -> Dict[str, Any]:
        """
        Create an invoice in Odoo.
        
        Args:
            customer_name: Customer name
            amount: Invoice amount
            description: Invoice description
            invoice_type: Type of invoice
            
        Returns:
            Invoice creation result
        """
        return self._make_jsonrpc_call(
            "account.move.create",
            {
                "move_type": invoice_type,
                "partner_name": customer_name,
                "invoice_line_ids": [
                    {
                        "product_name": description,
                        "quantity": 1,
                        "price_unit": amount
                    }
                ],
                "id": f"inv_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
    
    def list_invoices(self, limit: int = 50) -> Dict[str, Any]:
        """
        List invoices from Odoo.
        
        Args:
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoices
        """
        return self._make_jsonrpc_call(
            "account.move.search_read",
            {
                "domain": [],
                "fields": ["id", "name", "partner_name", "amount_total", "state", "invoice_date"],
                "limit": limit,
                "id": f"list_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )
    
    def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: Optional[str] = None,
        payment_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a payment for an invoice.
        
        Args:
            invoice_id: Invoice ID to pay
            amount: Payment amount
            payment_date: Payment date
            payment_reference: Payment reference
            
        Returns:
            Payment recording result
        """
        return self._make_jsonrpc_call(
            "account.payment.register.create",
            {
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_date": payment_date or datetime.now().strftime('%Y-%m-%d'),
                "payment_reference": payment_reference or f"PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "id": f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        )


# Initialize Odoo client
odoo_client = OdooJSONRPCClient(odoo_config)


# ============================================================
# Helper Functions
# ============================================================

def create_error_response(error: str, error_code: str, details: Optional[Dict] = None) -> Dict:
    """Create a standardized error response."""
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
        "details": details or {}
    }


def validate_odoo_config() -> tuple[bool, str]:
    """Validate Odoo configuration."""
    if not odoo_config.is_configured():
        return False, "Odoo credentials not configured. Check ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD"
    return True, "Odoo configured"


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    is_valid, _ = validate_odoo_config()
    
    return {
        "status": "healthy",
        "server": "odoo_mcp",
        "timestamp": datetime.now().isoformat(),
        "credentials_configured": is_valid,
        "jsonrpc_version": "2.0"
    }


@app.post("/jsonrpc", response_model=JSONRPCResponse)
async def jsonrpc_endpoint(request: JSONRPCRequest):
    """
    JSON-RPC 2.0 endpoint for Odoo operations.
    
    Supported methods:
    - create_invoice
    - list_invoices
    - record_payment
    
    Args:
        request: JSON-RPC request
        
    Returns:
        JSON-RPC response
    """
    action_logger.log_request(
        endpoint="/jsonrpc",
        method="POST",
        payload={"method": request.method, "params": request.params}
    )
    
    try:
        result = None
        
        if request.method == "create_invoice":
            if not request.params:
                raise HTTPException(status_code=400, detail="Missing params")
            
            result = odoo_client.create_invoice(
                customer_name=request.params.get("customer_name", "Customer"),
                amount=float(request.params.get("amount", 0)),
                description=request.params.get("description", "Invoice"),
                invoice_type=request.params.get("invoice_type", "out_invoice")
            )
            
        elif request.method == "list_invoices":
            limit = request.params.get("limit", 50) if request.params else 50
            result = odoo_client.list_invoices(limit=limit)
            
        elif request.method == "record_payment":
            if not request.params:
                raise HTTPException(status_code=400, detail="Missing params")
            
            result = odoo_client.record_payment(
                invoice_id=int(request.params.get("invoice_id", 0)),
                amount=float(request.params.get("amount", 0)),
                payment_date=request.params.get("payment_date"),
                payment_reference=request.params.get("payment_reference")
            )
        
        else:
            return JSONRPCResponse(
                jsonrpc="2.0",
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                },
                id=request.id
            )
        
        # Log the action
        status = "success" if "error" not in result else "error"
        log_to_system_log(
            action=f"jsonrpc:{request.method}",
            status=status,
            details={"request_id": request.id, "result": result.get("result") or result.get("error")}
        )
        
        action_logger.log_action(
            action=f"jsonrpc:{request.method}",
            status=status,
            details={"request_id": request.id, "result": result}
        )
        
        return JSONRPCResponse(
            jsonrpc="2.0",
            result=result.get("result"),
            error=result.get("error"),
            id=request.id
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"JSON-RPC error: {error_msg}")
        
        log_to_system_log(
            action=f"jsonrpc:{request.method}",
            status="error",
            details={"request_id": request.id, "error": error_msg}
        )
        
        return JSONRPCResponse(
            jsonrpc="2.0",
            error={
                "code": -32603,
                "message": "Internal error",
                "data": error_msg
            },
            id=request.id
        )


@app.post("/create_invoice", response_model=InvoiceResponse)
async def create_invoice(request: CreateInvoiceRequest):
    """
    Create an invoice in Odoo.
    
    Args:
        request: Invoice creation request
        
    Returns:
        Invoice creation result
    """
    action_logger.log_request(
        endpoint="/create_invoice",
        method="POST",
        payload=request.dict()
    )
    
    # Validate configuration
    is_valid, error_msg = validate_odoo_config()
    if not is_valid:
        action_logger.log_action(
            action="create_invoice",
            status="error",
            details={"error": error_msg}
        )
        log_to_system_log(
            action="create_invoice",
            status="error",
            details={"error": error_msg, "customer": request.customer_name}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        result = odoo_client.create_invoice(
            customer_name=request.customer_name,
            amount=request.amount,
            description=request.description,
            invoice_type=request.invoice_type
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"].get("message", "Odoo error"))
        
        invoice_data = result.get("result", {})
        
        action_logger.log_action(
            action="create_invoice",
            status="success",
            details={
                "invoice_id": invoice_data.get("id"),
                "customer": request.customer_name,
                "amount": request.amount
            }
        )
        
        log_to_system_log(
            action="create_invoice",
            status="success",
            details={
                "invoice_id": invoice_data.get("id"),
                "customer": request.customer_name,
                "amount": request.amount
            }
        )
        
        return InvoiceResponse(
            success=True,
            message="Invoice created successfully",
            data=invoice_data,
            invoice_id=invoice_data.get("id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to create invoice: {error_msg}")
        
        action_logger.log_action(
            action="create_invoice",
            status="error",
            details={"customer": request.customer_name, "error": error_msg}
        )
        
        log_to_system_log(
            action="create_invoice",
            status="error",
            details={"customer": request.customer_name, "error": error_msg}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {error_msg}")


@app.post("/list_invoices", response_model=ListInvoicesResponse)
async def list_invoices(limit: int = Field(default=50, ge=1, le=200)):
    """
    List invoices from Odoo.
    
    Args:
        limit: Maximum number of invoices to return
        
    Returns:
        List of invoices
    """
    action_logger.log_request(
        endpoint="/list_invoices",
        method="POST",
        payload={"limit": limit}
    )
    
    # Validate configuration
    is_valid, error_msg = validate_odoo_config()
    if not is_valid:
        action_logger.log_action(
            action="list_invoices",
            status="error",
            details={"error": error_msg}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        result = odoo_client.list_invoices(limit=limit)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"].get("message", "Odoo error"))
        
        invoices = result.get("result", [])
        
        action_logger.log_action(
            action="list_invoices",
            status="success",
            details={"count": len(invoices), "limit": limit}
        )
        
        log_to_system_log(
            action="list_invoices",
            status="success",
            details={"count": len(invoices), "limit": limit}
        )
        
        return ListInvoicesResponse(
            success=True,
            message=f"Retrieved {len(invoices)} invoices",
            invoices=invoices,
            count=len(invoices)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to list invoices: {error_msg}")
        
        action_logger.log_action(
            action="list_invoices",
            status="error",
            details={"error": error_msg}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to list invoices: {error_msg}")


@app.post("/record_payment", response_model=PaymentResponse)
async def record_payment(request: RecordPaymentRequest):
    """
    Record a payment for an invoice.
    
    Args:
        request: Payment recording request
        
    Returns:
        Payment recording result
    """
    action_logger.log_request(
        endpoint="/record_payment",
        method="POST",
        payload=request.dict()
    )
    
    # Validate configuration
    is_valid, error_msg = validate_odoo_config()
    if not is_valid:
        action_logger.log_action(
            action="record_payment",
            status="error",
            details={"error": error_msg}
        )
        log_to_system_log(
            action="record_payment",
            status="error",
            details={"error": error_msg, "invoice_id": request.invoice_id}
        )
        raise HTTPException(status_code=503, detail=error_msg)
    
    try:
        result = odoo_client.record_payment(
            invoice_id=request.invoice_id,
            amount=request.amount,
            payment_date=request.payment_date,
            payment_reference=request.payment_reference
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"].get("message", "Odoo error"))
        
        payment_data = result.get("result", {})
        
        action_logger.log_action(
            action="record_payment",
            status="success",
            details={
                "payment_id": payment_data.get("id"),
                "invoice_id": request.invoice_id,
                "amount": request.amount
            }
        )
        
        log_to_system_log(
            action="record_payment",
            status="success",
            details={
                "payment_id": payment_data.get("id"),
                "invoice_id": request.invoice_id,
                "amount": request.amount
            }
        )
        
        return PaymentResponse(
            success=True,
            message="Payment recorded successfully",
            data=payment_data,
            payment_id=payment_data.get("id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to record payment: {error_msg}")
        
        action_logger.log_action(
            action="record_payment",
            status="error",
            details={"invoice_id": request.invoice_id, "error": error_msg}
        )
        
        log_to_system_log(
            action="record_payment",
            status="error",
            details={"invoice_id": request.invoice_id, "error": error_msg}
        )
        
        raise HTTPException(status_code=500, detail=f"Failed to record payment: {error_msg}")


@app.get("/status")
async def server_status():
    """Get server status and configuration."""
    is_valid, _ = validate_odoo_config()
    
    return {
        "server": "odoo_mcp",
        "version": "1.0.0",
        "status": "running",
        "credentials_configured": is_valid,
        "jsonrpc_version": "2.0",
        "endpoints": [
            "/jsonrpc",
            "/create_invoice",
            "/list_invoices",
            "/record_payment",
            "/health",
            "/status"
        ],
        "config": {
            "url": odoo_config.url,
            "db": odoo_config.db,
            "username": odoo_config.username
        },
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# Error Handlers
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for all unhandled errors."""
    error_msg = str(exc)
    logger.error(f"Unhandled exception: {error_msg}")
    
    # Log to system log (graceful - don't crash)
    try:
        log_to_system_log(
            action="exception",
            status="error",
            details={
                "path": str(request.url.path),
                "method": request.method,
                "error": error_msg
            }
        )
    except Exception:
        pass  # Never crash even if logging fails
    
    action_logger.log_action(
        action="exception",
        status="error",
        details={
            "path": str(request.url.path),
            "method": request.method,
            "error": error_msg
        }
    )
    
    return {
        "success": False,
        "error": "Internal server error",
        "error_code": "INTERNAL_ERROR",
        "details": {"message": error_msg}
    }


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    # Get configuration from environment or use defaults
    host = os.getenv("ODOO_MCP_HOST", "127.0.0.1")
    port = int(os.getenv("ODOO_MCP_PORT", "8003"))
    
    logger.info(f"Starting Odoo MCP Server on http://{host}:{port}")
    logger.info("JSON-RPC 2.0 Endpoints available:")
    logger.info("  POST /jsonrpc - JSON-RPC endpoint (all methods)")
    logger.info("  POST /create_invoice - Create an invoice")
    logger.info("  POST /list_invoices - List invoices")
    logger.info("  POST /record_payment - Record a payment")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /status - Server status")
    logger.info("")
    logger.info("Environment variables:")
    logger.info(f"  ODOO_URL: {odoo_config.url}")
    logger.info(f"  ODOO_DB: {odoo_config.db}")
    logger.info(f"  ODOO_USERNAME: {odoo_config.username}")
    logger.info(f"  ODOO_PASSWORD: {'*' * len(odoo_config.password) if odoo_config.password else 'not set'}")
    
    uvicorn.run(app, host=host, port=port)
