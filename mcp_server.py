import asyncio
import hashlib
import hmac
import json
import os
import secrets
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
import decimal

# ── Global configuration ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_PATH = os.path.join(BASE_DIR, "target", "debug", "tempus-ddb")
SANDBOX_DIR = os.path.realpath(BASE_DIR)
WALLET_FILE = os.path.join(SANDBOX_DIR, "agent_wallet.json")
SECRET_KEY_FILE = os.path.join(SANDBOX_DIR, "server_secret.key")
COST_PER_RECORD = decimal.Decimal("0.01")

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


def _compute_hmac(balance) -> str:
    """Compute HMAC-SHA256 of the balance value."""
    msg = json.dumps(float(balance), sort_keys=True).encode()
    return hmac.new(_SERVER_SECRET, msg, hashlib.sha256).hexdigest()


# ── Wallet helpers (C1 – HMAC integrity) ──────────────────────────────
def load_wallet() -> dict:
    if not os.path.exists(WALLET_FILE):
        return {"balance_usdc": decimal.Decimal("0.0")}
    with open(WALLET_FILE, "r") as f:
        data = json.load(f, parse_float=decimal.Decimal)
    if "balance_usdc" in data and not isinstance(data["balance_usdc"], decimal.Decimal):
        data["balance_usdc"] = decimal.Decimal(str(data["balance_usdc"]))
    # Verify HMAC
    stored_hmac = data.get("hmac")
    if stored_hmac is None:
        raise RuntimeError("Wallet integrity check failed: missing HMAC signature.")
    expected = _compute_hmac(data["balance_usdc"])
    if not hmac.compare_digest(stored_hmac, expected):
        raise RuntimeError("Wallet integrity check failed: HMAC mismatch – wallet may have been tampered with.")
    return data


def save_wallet(wallet: dict) -> None:
    wallet["hmac"] = _compute_hmac(wallet["balance_usdc"])
    wallet_copy = wallet.copy()
    wallet_copy["balance_usdc"] = float(wallet["balance_usdc"])
    with open(WALLET_FILE, "w") as f:
        json.dump(wallet_copy, f, indent=2)


# ── Path-traversal guard (C3) ─────────────────────────────────────────
def validate_path(path: str) -> str:
    """Resolve *path* and ensure it stays inside SANDBOX_DIR."""
    resolved = os.path.realpath(os.path.join(SANDBOX_DIR, path))
    if ".." in os.path.normpath(path).split(os.sep):
        raise ValueError(f"Path contains disallowed '..': {path}")
    if not resolved.startswith(SANDBOX_DIR + os.sep) and resolved != SANDBOX_DIR:
        raise ValueError(f"Path escapes sandbox: {path}")
    return resolved


# ── Async subprocess runner (C8) ──────────────────────────────────────
async def run_cmd_async(args: list[str]) -> str:
    """Run the Rust binary via asyncio subprocess instead of blocking subprocess.run."""
    cmd = [BIN_PATH] + args
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Error ejecutando {' '.join(args)}:\n{stderr.decode()}")
    return stdout.decode().strip()


# ── Input validation helpers (H4) ─────────────────────────────────────
def validate_json_string(value: str, field_name: str) -> None:
    """Ensure *value* is a valid JSON string."""
    try:
        json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"'{field_name}' must be a valid JSON string: {exc}")


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
            description="Record a new decision in the local ledger. Costs 0.01 USDC per call.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "payload": {"type": "string", "description": "JSON payload representing the decision"},
                    "rules": {"type": "string", "description": "JSON rules representing the logic applied"},
                    "keyfile": {"type": "string", "description": "Path to the keys.json file"},
                    "parent": {"type": "string", "description": "ID of the parent decision. Omit for genesis."},
                    "genesis": {"type": "boolean", "description": "True if this is the first decision in the chain."}
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
            name="tempus_fund_wallet",
            description="Transfer simulated funds to the agent's wallet to pay for Tempus API calls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "Amount to fund in USDC"}
                },
                "required": ["amount"]
            }
        ),
        Tool(
            name="tempus_cleanup",
            description="Delete the database and keys in the sandbox to start fresh.",
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
            db = validate_path(arguments.get("db", "tempus_ddb.db"))
            output = await run_cmd_async(["init", "--db", db])
            return [TextContent(type="text", text=f"Database initialized: {db}")]

        elif name == "tempus_gen_keys":
            output_file = validate_path(arguments.get("output", "keys.json"))
            output = await run_cmd_async(["gen-keys", "--output", output_file])
            return [TextContent(type="text", text=f"Keys generated at {output_file}:\n{output}")]

        elif name == "tempus_record":
            # ── Validate JSON inputs (H4) ──
            payload = arguments["payload"]
            rules = arguments["rules"]
            validate_json_string(payload, "payload")
            validate_json_string(rules, "rules")

            # ── Validate file paths (C3) ──
            db = validate_path(arguments["db"])
            keyfile = validate_path(arguments["keyfile"])

            # ── Atomic wallet check-deduct under lock (C8) ──
            async with _wallet_lock:
                wallet = load_wallet()
                if wallet["balance_usdc"] < COST_PER_RECORD:
                    error_response = {
                        "error": "insufficient_funds",
                        "action_required": "send_crypto",
                        "amount": float(COST_PER_RECORD),
                        "currency": "USDC",
                        "wallet_address": "0xTEMPUSAGENTWALLET123456",
                        "message": "You must fund your wallet using the 'tempus_fund_wallet' tool before calling 'tempus_record'."
                    }
                    return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

                args_list = ["record", "--db", db, "--payload", payload, "--rules", rules, "--keyfile", keyfile]
                if arguments.get("parent"):
                    args_list.extend(["--parent", arguments["parent"]])
                if arguments.get("genesis"):
                    args_list.append("--genesis")

                output = await run_cmd_async(args_list)

                # Deduct funds
                wallet["balance_usdc"] -= COST_PER_RECORD
                save_wallet(wallet)

            return [TextContent(type="text", text=f"Record successful. Remaining balance: {wallet['balance_usdc']:.2f} USDC.\nOutput:\n{output}")]

        elif name == "tempus_validate":
            db = validate_path(arguments.get("db", "tempus_ddb.db"))
            output = await run_cmd_async(["validate", "--db", db])
            return [TextContent(type="text", text=output)]

        elif name == "tempus_fund_wallet":
            amount = decimal.Decimal(str(arguments["amount"]))
            # ── Reject non-positive amounts (C1 / H4) ──
            if amount <= 0:
                raise ValueError("Funding amount must be a positive number.")

            async with _wallet_lock:
                wallet = load_wallet()
                wallet["balance_usdc"] += amount
                save_wallet(wallet)
            return [TextContent(type="text", text=f"Wallet successfully funded with {amount} USDC. New balance: {float(wallet['balance_usdc']):.2f} USDC.")]

        elif name == "tempus_cleanup":
            async with _wallet_lock:
                db_path = os.path.join(SANDBOX_DIR, "tempus_ddb.db")
                keys_path = os.path.join(SANDBOX_DIR, "keys.json")
                if os.path.exists(db_path):
                    os.remove(db_path)
                if os.path.exists(keys_path):
                    os.remove(keys_path)
            return [TextContent(type="text", text="Cleanup successful. Database and keys deleted.")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        err_msg = str(e)
        if isinstance(e, RuntimeError) and "Error ejecutando" in err_msg:
            return [TextContent(type="text", text="Error: Subprocess command failed.")]
        return [TextContent(type="text", text=f"Error executing tool {name}: {err_msg}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
