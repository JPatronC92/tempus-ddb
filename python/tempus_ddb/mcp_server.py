import asyncio
import hashlib
import hmac
import json
import os
import secrets
import decimal
import string
import time
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from dotenv import load_dotenv

load_dotenv()

# ── Global configuration ──────────────────────────────────────────────
SANDBOX_DIR = os.path.realpath(os.getcwd())
WALLET_FILE = os.path.join(SANDBOX_DIR, "agent_wallet.json")
SECRET_KEY_FILE = os.path.join(SANDBOX_DIR, "server_secret.key")
COST_PER_RECORD = decimal.Decimal("0.01")
TEMPUS_MODE = os.environ.get("TEMPUS_MODE", "demo")
MODE_WARNING = "DemoPaymentAdapter is active. No real USDC was transferred." if TEMPUS_MODE == "demo" else ""

# ── Async lock for wallet operations (C8) ─────────────────────────────
_wallet_lock = asyncio.Lock()

# ── Server secret for HMAC (C1) ───────────────────────────────────────
def _get_or_create_secret() -> bytes:
    """Load existing secret key, or generate a new 32-byte random key."""
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "rb") as f:
            return f.read()
    secret = secrets.token_bytes(32)
    with open(SECRET_KEY_FILE, "wb") as f:
        f.write(secret)
    return secret

_SERVER_SECRET = _get_or_create_secret()


def _compute_hmac(agents_dict) -> str:
    """Compute HMAC-SHA256 of the agents dictionary data."""
    canonical_data = {}
    for aid, info in sorted(agents_dict.items()):
        canonical_data[aid] = {
            "balance_usdc": float(info["balance_usdc"]),
            "reserved_balance_usdc": float(info.get("reserved_balance_usdc", 0.0)),
            "economic_events": info.get("economic_events", []),
            "idempotency_keys": info.get("idempotency_keys", {}),
            "used_funding_txs": info.get("used_funding_txs", [])
        }
    msg = json.dumps(canonical_data, sort_keys=True).encode()
    return hmac.new(_SERVER_SECRET, msg, hashlib.sha256).hexdigest()


# ── Wallet helpers (C1 – HMAC integrity) ──────────────────────────────
def load_wallet() -> dict:
    if not os.path.exists(WALLET_FILE):
        default_wallet = {"agents": {}}
        save_wallet(default_wallet)
        return default_wallet
    with open(WALLET_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    # Migrate old schema to new multi-agent schema if needed
    if "balance_usdc" in data and "agents" not in data:
        old_balance = decimal.Decimal(str(data.get("balance_usdc", 0.0)))
        default_agent = {
            "balance_usdc": old_balance,
            "reserved_balance_usdc": decimal.Decimal("0.0"),
            "economic_events": [
                {
                    "type": "wallet_funded",
                    "amount": float(old_balance),
                    "reason": "migration_from_old_schema",
                    "timestamp": int(time.time())
                }
            ],
            "idempotency_keys": {}
        }
        data = {
            "agents": {
                "default_agent": default_agent
            }
        }

    agents = data.get("agents", {})
    # Convert float balances back to decimal
    for aid, info in agents.items():
        info["balance_usdc"] = decimal.Decimal(str(info.get("balance_usdc", 0.0)))
        info["reserved_balance_usdc"] = decimal.Decimal(str(info.get("reserved_balance_usdc", 0.0)))
        if "economic_events" not in info:
            info["economic_events"] = []
        if "idempotency_keys" not in info:
            info["idempotency_keys"] = {}
    
    # Verify HMAC
    stored_hmac = data.get("hmac")
    if stored_hmac is None:
        raise RuntimeError("TEMPUS_WALLET_INTEGRITY_FAILURE: missing HMAC signature.")
    expected = _compute_hmac(agents)
    if not hmac.compare_digest(stored_hmac, expected):
        raise RuntimeError("TEMPUS_WALLET_INTEGRITY_FAILURE: HMAC mismatch – wallet may have been tampered with.")
    return {"agents": agents}


def save_wallet(wallet: dict) -> None:
    agents = wallet.get("agents", {})
    # Compute HMAC
    hmac_val = _compute_hmac(agents)
    
    # Prepare serializable copy
    serializable_agents = {}
    for aid, info in agents.items():
        serializable_agents[aid] = {
            "balance_usdc": float(info["balance_usdc"]),
            "reserved_balance_usdc": float(info.get("reserved_balance_usdc", 0.0)),
            "economic_events": info.get("economic_events", []),
            "idempotency_keys": info.get("idempotency_keys", {})
        }
    
    output_data = {
        "agents": serializable_agents,
        "hmac": hmac_val
    }
    with open(WALLET_FILE, "w") as f:
        json.dump(output_data, f, indent=2)


def get_or_create_agent(wallet: dict, agent_id: str) -> dict:
    if agent_id not in wallet["agents"]:
        wallet["agents"][agent_id] = {
            "balance_usdc": decimal.Decimal("0.0"),
            "reserved_balance_usdc": decimal.Decimal("0.0"),
            "economic_events": [],
            "idempotency_keys": {}
        }
    info = wallet["agents"][agent_id]
    if "reserved_balance_usdc" not in info:
        info["reserved_balance_usdc"] = decimal.Decimal("0.0")
    if "economic_events" not in info:
        info["economic_events"] = []
    if "idempotency_keys" not in info:
        info["idempotency_keys"] = {}
    return info


def log_event(agent_info: dict, event_type: str, amount: decimal.Decimal, reason: str):
    agent_info["economic_events"].append({
        "type": event_type,
        "amount": float(amount),
        "reason": reason,
        "timestamp": int(time.time())
    })


# ── Path-traversal guard (C3) ─────────────────────────────────────────
def validate_path(path: str) -> str:
    """Resolve *path* and ensure it stays inside SANDBOX_DIR."""
    resolved = os.path.realpath(os.path.join(SANDBOX_DIR, path))
    if ".." in os.path.normpath(path).split(os.sep):
        raise ValueError(f"Path contains disallowed '..': {path}")
    if not resolved.startswith(SANDBOX_DIR + os.sep) and resolved != SANDBOX_DIR:
        raise ValueError(f"Path escapes sandbox: {path}")
    return resolved

# ── Import PyO3 native module and Generate Local License ────────────────
import tempus_ddb

def _generate_local_license() -> str:
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(24))
    hmac_sig = hmac.new(b"tempus-ddb-hmac-secret-key-v1-2026", random_part.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"tmb_live_{random_part}_{hmac_sig}"

LOCAL_LICENSE = _generate_local_license()


# ── Input validation helpers (H4) ─────────────────────────────────────
def validate_json_string(value: str, field_name: str) -> None:
    """Ensure *value* is a valid JSON string."""
    try:
        json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"'{field_name}' must be a valid JSON string: {exc}")


# ── B2A Payment Adapter Abstraction (Task 7 / Task 1 / Task 3) ─────────
class PaymentAdapter:
    """Interface / Adapter for wallet operations."""
    async def get_balance(self, agent_id: str) -> dict:
        raise NotImplementedError
        
    async def deduct_funds(self, agent_id: str, amount: decimal.Decimal) -> None:
        raise NotImplementedError

    async def add_funds(self, agent_id: str, amount: decimal.Decimal) -> None:
        raise NotImplementedError


class DemoPaymentAdapter(PaymentAdapter):
    """Local JSON-based demo wallet payment adapter supporting multi-agents and reserves."""
    def __init__(self, wallet_file: str, lock: asyncio.Lock):
        self.wallet_file = wallet_file
        self.lock = lock

    async def get_balance(self, agent_id: str) -> dict:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            return {
                "balance_usdc": agent_info["balance_usdc"],
                "reserved_balance_usdc": agent_info["reserved_balance_usdc"]
            }

    async def add_funds(self, agent_id: str, amount: decimal.Decimal, reason: str = "funding") -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            agent_info["balance_usdc"] += amount
            log_event(agent_info, "wallet_funded", amount, reason)
            save_wallet(wallet)

    async def charge(self, agent_id: str, amount: decimal.Decimal, reason: str) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            if agent_info["balance_usdc"] < amount:
                log_event(agent_info, "charge_failed", amount, f"insufficient_funds:{reason}")
                save_wallet(wallet)
                raise ValueError("TEMPUS_INSUFFICIENT_FUNDS")
            agent_info["balance_usdc"] -= amount
            log_event(agent_info, "charge_committed", amount, reason)
            save_wallet(wallet)

    async def refund(self, agent_id: str, amount: decimal.Decimal, reason: str) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            agent_info["balance_usdc"] += amount
            log_event(agent_info, "charge_refunded", amount, reason)
            save_wallet(wallet)

    async def reserve_charge(self, agent_id: str, amount: decimal.Decimal, reason: str) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            if agent_info["balance_usdc"] < amount:
                log_event(agent_info, "charge_failed", amount, f"reserve_insufficient_funds:{reason}")
                save_wallet(wallet)
                raise ValueError("TEMPUS_INSUFFICIENT_FUNDS")
            agent_info["balance_usdc"] -= amount
            agent_info["reserved_balance_usdc"] += amount
            log_event(agent_info, "charge_reserved", amount, reason)
            save_wallet(wallet)

    async def commit_charge(self, agent_id: str, amount: decimal.Decimal, reason: str) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            if agent_info["reserved_balance_usdc"] < amount:
                log_event(agent_info, "charge_failed", amount, f"commit_no_reserve:{reason}")
                save_wallet(wallet)
                raise ValueError("TEMPUS_PAYMENT_COMMIT_FAILED")
            agent_info["reserved_balance_usdc"] -= amount
            log_event(agent_info, "charge_committed", amount, reason)
            save_wallet(wallet)

    async def refund_charge(self, agent_id: str, amount: decimal.Decimal, reason: str) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            if agent_info["reserved_balance_usdc"] < amount:
                agent_info["balance_usdc"] += amount
            else:
                agent_info["reserved_balance_usdc"] -= amount
                agent_info["balance_usdc"] += amount
            log_event(agent_info, "charge_refunded", amount, reason)
            save_wallet(wallet)

    async def check_idempotency(self, agent_id: str, idempotency_key: str) -> dict:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            return agent_info["idempotency_keys"].get(idempotency_key)

    async def save_idempotency(self, agent_id: str, idempotency_key: str, response: dict) -> None:
        async with self.lock:
            wallet = load_wallet()
            agent_info = get_or_create_agent(wallet, agent_id)
            agent_info["idempotency_keys"][idempotency_key] = response
            save_wallet(wallet)


_PAYMENT_ADAPTER = DemoPaymentAdapter(WALLET_FILE, _wallet_lock)


# ── MCP server setup ──────────────────────────────────────────────────
app = Server("tempus-ddb-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="tempus_init",
            description="Initialize the SQLite database schema for Tempus DDB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"}
                },
                "required": ["db"]
            }
        ),
        Tool(
            name="tempus_gen_keys",
            description="Generate a new Ed25519 cryptographic keypair.",
            inputSchema={
                "type": "object",
                "properties": {
                    "output": {"type": "string", "description": "Key file output path"}
                },
                "required": ["output"]
            }
        ),
        Tool(
            name="tempus_record",
            description="Record a new decision in the local ledger. Costs 0.01 USDC per call (alias of tempus_record_decision).",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "payload": {"type": "string", "description": "JSON payload representing the decision"},
                    "rules": {"type": "string", "description": "JSON rules representing the logic applied"},
                    "keyfile": {"type": "string", "description": "Path to the keys.json file"},
                    "parent": {"type": "string", "description": "ID of the parent decision. Omit for genesis."},
                    "genesis": {"type": "boolean", "description": "True if this is the first decision in the chain."},
                    "agent_id": {"type": "string", "description": "Agent identifier for payment accounting."},
                    "idempotency_key": {"type": "string", "description": "Unique key to ensure idempotent retries."}
                },
                "required": ["db", "payload", "rules", "keyfile"]
            }
        ),
        Tool(
            name="tempus_record_decision",
            description="Record a new decision in the local ledger. Costs 0.01 USDC per call.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "payload": {"type": "string", "description": "JSON payload representing the decision"},
                    "rules": {"type": "string", "description": "JSON rules representing the logic applied"},
                    "keyfile": {"type": "string", "description": "Path to the keys.json file"},
                    "parent": {"type": "string", "description": "ID of the parent decision. Omit for genesis."},
                    "genesis": {"type": "boolean", "description": "True if this is the first decision in the chain."},
                    "agent_id": {"type": "string", "description": "Agent identifier for payment accounting."},
                    "idempotency_key": {"type": "string", "description": "Unique key to ensure idempotent retries."}
                },
                "required": ["db", "payload", "rules", "keyfile"]
            }
        ),
        Tool(
            name="tempus_validate",
            description="Validate the cryptographic integrity of the decision chain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"}
                },
                "required": ["db"]
            }
        ),
        Tool(
            name="tempus_check_balance",
            description="Check the current balance of the agent's wallet in USDC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent identifier."}
                },
                "required": []
            }
        ),
        Tool(
            name="tempus_fund_wallet",
            description="Transfer simulated funds to the agent's wallet to pay for Tempus API calls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to fund in USDC (used in demo mode)."},
                    "agent_id": {"type": "string", "description": "Agent identifier."},
                    "tx_hash": {"type": "string", "description": "Transaction hash on the blockchain (required for web3-testnet mode)."},
                    "network": {"type": "string", "description": "Blockchain network (e.g. 'base-sepolia')."}
                },
                "required": []
            }
        ),
        Tool(
            name="tempus_cleanup",
            description="Delete the database, keys and wallet in the sandbox to start fresh.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "tempus_init":
            db_path = validate_path(arguments.get("db", "tempus_ddb.db"))
            db = tempus_ddb.TempusDDB(LOCAL_LICENSE, db_path, "keys.json")
            success_response = {
                "status": "success",
                "message": f"Database initialized: {db_path}",
                "db_path": db_path
            }
            if TEMPUS_MODE == "demo":
                success_response["mode"] = TEMPUS_MODE
                success_response["warning"] = MODE_WARNING
            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        elif name == "tempus_gen_keys":
            output_file = validate_path(arguments.get("output", "keys.json"))
            output = tempus_ddb.gen_keys(output_file)
            try:
                output_json = json.loads(output)
            except Exception:
                output_json = output
            success_response = {
                "status": "success",
                "message": f"Keys generated at {output_file}",
                "key_file": output_file,
                "output": output_json
            }
            if TEMPUS_MODE == "demo":
                success_response["mode"] = TEMPUS_MODE
                success_response["warning"] = MODE_WARNING
            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        elif name in ("tempus_record", "tempus_record_decision"):
            # ── Validate JSON inputs (H4) ──
            payload = arguments["payload"]
            rules = arguments["rules"]
            validate_json_string(payload, "payload")
            validate_json_string(rules, "rules")

            # ── Validate file paths (C3) ──
            db = validate_path(arguments["db"])
            keyfile = validate_path(arguments["keyfile"])

            agent_id = arguments.get("agent_id", "default_agent")
            idempotency_key = arguments.get("idempotency_key")

            # ── Idempotency Check (Task 2) ──
            if idempotency_key:
                existing_res = await _PAYMENT_ADAPTER.check_idempotency(agent_id, idempotency_key)
                if existing_res:
                    if existing_res.get("status") == "PENDING_COMMIT":
                        # We must complete the commit
                        try:
                            await _PAYMENT_ADAPTER.commit_charge(agent_id, COST_PER_RECORD, f"record_decision:{idempotency_key}")
                            existing_res["status"] = "success"
                            new_balance_info = await _PAYMENT_ADAPTER.get_balance(agent_id)
                            existing_res["remaining_balance_usdc"] = float(new_balance_info["balance_usdc"])
                            await _PAYMENT_ADAPTER.save_idempotency(agent_id, idempotency_key, existing_res)
                        except Exception as e:
                            raise ValueError(f"TEMPUS_PAYMENT_COMMIT_FAILED: {str(e)}")
                    return [TextContent(type="text", text=json.dumps(existing_res, indent=2))]

            # ── Reserve Charge (Task 3) ──
            try:
                await _PAYMENT_ADAPTER.reserve_charge(agent_id, COST_PER_RECORD, f"record_decision:{idempotency_key or 'direct'}")
            except ValueError as exc:
                if str(exc) == "TEMPUS_INSUFFICIENT_FUNDS":
                    error_response = {
                        "status": "error",
                        "error": "TEMPUS_INSUFFICIENT_FUNDS",
                        "error_code": "insufficient_funds",
                        "action_required": "send_crypto",
                        "amount": float(COST_PER_RECORD),
                        "currency": "USDC",
                        "wallet_address": "0xTEMPUSAGENTWALLET123456",
                        "message": "You must fund your wallet using the 'tempus_fund_wallet' tool before recording decisions.",
                        "next_action": "tempus_fund_wallet",
                        "retry_tool": "tempus_record_decision"
                    }
                    return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
                raise

            genesis = arguments.get("genesis", False)
            try:
                db_instance = tempus_ddb.TempusDDB(LOCAL_LICENSE, db, keyfile)
                output = db_instance.record(payload, rules, genesis)
            except Exception as record_exc:
                # ── Refund Charge on Failure (Task 3) ──
                await _PAYMENT_ADAPTER.refund_charge(agent_id, COST_PER_RECORD, f"record_decision_failed:{idempotency_key or 'direct'}")
                raise record_exc

            # ── Save PENDING_COMMIT State (Task 6) ──
            success_response = {
                "status": "PENDING_COMMIT",
                "message": "Record successful but commit pending.",
                "cost_incurred_usdc": float(COST_PER_RECORD),
                "output": json.loads(output) if isinstance(output, str) and (output.strip().startswith("{") or output.strip().startswith("[")) else output
            }
            if TEMPUS_MODE == "demo":
                success_response["mode"] = TEMPUS_MODE
                success_response["warning"] = MODE_WARNING

            if idempotency_key:
                await _PAYMENT_ADAPTER.save_idempotency(agent_id, idempotency_key, success_response)

            # ── Commit Charge (Task 3) ──
            try:
                await _PAYMENT_ADAPTER.commit_charge(agent_id, COST_PER_RECORD, f"record_decision:{idempotency_key or 'direct'}")
            except Exception as e:
                raise ValueError(f"TEMPUS_PAYMENT_COMMIT_FAILED: {str(e)}")

            success_response["status"] = "success"
            success_response["message"] = "Record successful."
            new_balance_info = await _PAYMENT_ADAPTER.get_balance(agent_id)
            success_response["remaining_balance_usdc"] = float(new_balance_info["balance_usdc"])

            # ── Save Idempotency (Task 2) ──
            if idempotency_key:
                await _PAYMENT_ADAPTER.save_idempotency(agent_id, idempotency_key, success_response)

            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        elif name == "tempus_validate":
            db_path = validate_path(arguments.get("db", "tempus_ddb.db"))
            db = tempus_ddb.TempusDDB(LOCAL_LICENSE, db_path, "keys.json")
            try:
                output = db.validate()
                out_str = str(output).lower()
                if "invalid" in out_str or "mismatch" in out_str or "error" in out_str:
                    raise RuntimeError(f"TEMPUS_LEDGER_INTEGRITY_FAILURE: {output}")
            except Exception as e:
                if "TEMPUS_LEDGER_INTEGRITY_FAILURE" not in str(e):
                    raise RuntimeError(f"TEMPUS_LEDGER_INTEGRITY_FAILURE: {str(e)}")
                raise

            success_response = {
                "status": "success",
                "message": "Validation query completed.",
                "db_path": db_path,
                "result": output
            }
            if TEMPUS_MODE == "demo":
                success_response["mode"] = TEMPUS_MODE
                success_response["warning"] = MODE_WARNING
            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        elif name == "tempus_check_balance":
            agent_id = arguments.get("agent_id", "default_agent")
            balance_info = await _PAYMENT_ADAPTER.get_balance(agent_id)
            
            async with _wallet_lock:
                wallet = load_wallet()
                agent_info = get_or_create_agent(wallet, agent_id)
                events = agent_info.get("economic_events", [])
            
            response = {
                "status": "success",
                "balance_usdc": float(balance_info["balance_usdc"]),
                "reserved_balance_usdc": float(balance_info["reserved_balance_usdc"]),
                "currency": "USDC",
                "wallet_address": "0xTEMPUSAGENTWALLET123456",
                "economic_events": events
            }
            if TEMPUS_MODE == "demo":
                response["mode"] = TEMPUS_MODE
                response["warning"] = MODE_WARNING
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        elif name == "tempus_fund_wallet":
            agent_id = arguments.get("agent_id", "default_agent")
            
            if TEMPUS_MODE == "web3-testnet":
                tx_hash = arguments.get("tx_hash")
                network = arguments.get("network", "base-sepolia")
                if not tx_hash:
                    raise ValueError("TEMPUS_MISSING_TX_HASH: 'tx_hash' is required in web3-testnet mode.")
                
                async with _wallet_lock:
                    wallet = load_wallet()
                    agent_info = get_or_create_agent(wallet, agent_id)
                    used_txs = agent_info.get("used_funding_txs", [])
                    if tx_hash in used_txs:
                        raise ValueError(f"TEMPUS_DUPLICATE_FUNDING_TX: Transaction {tx_hash} has already been used.")

                from .web3_adapter import Web3PaymentAdapter
                adapter = Web3PaymentAdapter()
                amount_val = await adapter.verify_funding_tx(network, tx_hash)
                amount = decimal.Decimal(str(amount_val))
                
                async with _wallet_lock:
                    wallet = load_wallet()
                    agent_info = get_or_create_agent(wallet, agent_id)
                    agent_info.setdefault("used_funding_txs", []).append(tx_hash)
                    save_wallet(wallet)
            else:
                if "amount" not in arguments:
                    raise ValueError("TEMPUS_MISSING_AMOUNT: 'amount' is required in demo mode.")
                amount = decimal.Decimal(str(arguments["amount"]))
                if amount <= 0:
                    raise ValueError("Funding amount must be a positive number.")

            await _PAYMENT_ADAPTER.add_funds(agent_id, amount)
            balance_info = await _PAYMENT_ADAPTER.get_balance(agent_id)
            success_response = {
                "status": "success",
                "message": f"Wallet successfully funded with {amount} USDC.",
                "funded_amount_usdc": float(amount),
                "new_balance_usdc": float(balance_info["balance_usdc"]),
                "currency": "USDC"
            }
            if TEMPUS_MODE == "demo":
                success_response["mode"] = TEMPUS_MODE
                success_response["warning"] = MODE_WARNING
            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        elif name == "tempus_cleanup":
            async with _wallet_lock:
                db_path = os.path.join(SANDBOX_DIR, "tempus_ddb.db")
                keys_path = os.path.join(SANDBOX_DIR, "keys.json")
                if os.path.exists(db_path):
                    os.remove(db_path)
                if os.path.exists(keys_path):
                    os.remove(keys_path)
                if os.path.exists(WALLET_FILE):
                    os.remove(WALLET_FILE)
            success_response = {
                "status": "success",
                "message": "Cleanup successful. Database, keys, and wallet deleted."
            }
            return [TextContent(type="text", text=json.dumps(success_response, indent=2))]

        else:
            error_response = {
                "status": "error",
                "error": "TEMPUS_UNKNOWN_TOOL",
                "message": f"Unknown tool: {name}"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
    except Exception as e:
        err_msg = str(e)
        
        # Check for specific known errors to return cleanly
        error_code = "TEMPUS_EXECUTION_ERROR"
        for known_err in [
            "TEMPUS_WALLET_INTEGRITY_FAILURE",
            "TEMPUS_LEDGER_INTEGRITY_FAILURE",
            "TEMPUS_PAYMENT_COMMIT_FAILED",
            "TEMPUS_PAYMENT_RESERVATION_FAILED",
            "TEMPUS_RECORD_FAILED",
            "TEMPUS_INVALID_AGENT_ID",
            "TEMPUS_INVALID_IDEMPOTENCY_KEY"
        ]:
            if known_err in err_msg:
                error_code = known_err
                break

        error_response = {
            "status": "error",
            "error": error_code,
            "tool": name,
            "message": err_msg
        }
        if TEMPUS_MODE == "demo":
            error_response["mode"] = TEMPUS_MODE
            error_response["warning"] = MODE_WARNING
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

async def main():
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except KeyboardInterrupt:
        pass

def main_sync():
    """Entry point for the tempus-mcp console script."""
    asyncio.run(main())

if __name__ == "__main__":
    main_sync()
