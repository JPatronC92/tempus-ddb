import asyncio
import json
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from dotenv import load_dotenv

load_dotenv()

# ── Global configuration ──────────────────────────────────────────────
SANDBOX_DIR = os.path.realpath(os.getcwd())
TEMPUS_MODE = os.environ.get("TEMPUS_MODE", "demo")

# ── Path-traversal guard ──────────────────────────────────────────────
def validate_path(path: str) -> str:
    """Resolve *path* and ensure it stays inside SANDBOX_DIR."""
    resolved = os.path.realpath(os.path.join(SANDBOX_DIR, path))
    if ".." in os.path.normpath(path).split(os.sep):
        raise ValueError(f"Path contains disallowed '..': {path}")
    if not resolved.startswith(SANDBOX_DIR + os.sep) and resolved != SANDBOX_DIR:
        raise ValueError(f"Path escapes sandbox: {path}")
    return resolved

# ── Import PyO3 native module ────────────────
from ._tempus_ddb import TempusDDB, gen_keys

# ── Input validation helpers ─────────────────────────────────────
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
            name="tempus_record_decision",
            description="Record a new decision in the local ledger. Alias: tempus_record.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "payload": {"type": "string", "description": "JSON payload representing the decision"},
                    "rules": {"type": "string", "description": "JSON rules representing the logic applied"},
                    "keyfile": {"type": "string", "description": "Path to the keys.json file"},
                    "genesis": {"type": "boolean", "description": "True if this is the first decision in the chain."},
                },
                "required": ["db", "payload", "rules", "keyfile"]
            }
        ),
        Tool(
            name="tempus_record",
            description="Alias for tempus_record_decision. Record a new decision in the local ledger.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "payload": {"type": "string", "description": "JSON payload representing the decision"},
                    "rules": {"type": "string", "description": "JSON rules representing the logic applied"},
                    "keyfile": {"type": "string", "description": "Path to the keys.json file"},
                    "genesis": {"type": "boolean", "description": "True if this is the first decision in the chain."},
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
            name="tempus_list",
            description="List decisions in the ledger with optional pagination. Returns most recent first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"},
                    "limit": {"type": "integer", "description": "Maximum number of records to return (default: 10)"},
                    "offset": {"type": "integer", "description": "Number of records to skip (default: 0)"},
                },
                "required": ["db"]
            }
        ),
        Tool(
            name="tempus_export",
            description="Export all decisions as a JSON array ordered by causal depth.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"}
                },
                "required": ["db"]
            }
        ),
        Tool(
            name="tempus_count",
            description="Count the total number of decisions in the ledger.",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "Database file path"}
                },
                "required": ["db"]
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


def _handle_record(arguments: dict) -> list[TextContent]:
    """Shared implementation for tempus_record and tempus_record_decision."""
    payload = arguments["payload"]
    rules = arguments["rules"]
    validate_json_string(payload, "payload")
    validate_json_string(rules, "rules")

    db = validate_path(arguments["db"])
    keyfile = validate_path(arguments["keyfile"])

    genesis = arguments.get("genesis", False)

    db_instance = TempusDDB(db, keyfile)
    output = db_instance.record(payload, rules, genesis)

    result = {
        "status": "success",
        "message": "Record successful.",
        "output": json.loads(output) if isinstance(output, str) and (output.strip().startswith("{") or output.strip().startswith("[")) else output
    }
    if TEMPUS_MODE == "demo":
        result["mode"] = TEMPUS_MODE
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "tempus_init":
            db_path = validate_path(arguments.get("db", "tempus.db"))
            db = TempusDDB(db_path, "keys.json")
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": f"Database initialized: {db_path}",
                "db_path": db_path
            }, indent=2))]

        elif name == "tempus_gen_keys":
            output_file = validate_path(arguments.get("output", "keys.json"))
            output = gen_keys(output_file)
            try:
                output_json = json.loads(output)
                if isinstance(output_json, dict) and "private_key" in output_json:
                    del output_json["private_key"]
            except Exception:
                output_json = output
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": f"Keys generated at {output_file}",
                "key_file": output_file,
                "output": output_json
            }, indent=2))]

        elif name in ("tempus_record", "tempus_record_decision"):
            return _handle_record(arguments)

        elif name == "tempus_validate":
            db_path = validate_path(arguments.get("db", "tempus.db"))
            db = TempusDDB(db_path, "keys.json")
            try:
                output = db.validate()
                out_str = str(output).lower()
                if "invalid" in out_str or "mismatch" in out_str or "error" in out_str:
                    raise RuntimeError(f"TEMPUS_LEDGER_INTEGRITY_FAILURE: {output}")
            except Exception as e:
                if "TEMPUS_LEDGER_INTEGRITY_FAILURE" not in str(e):
                    raise RuntimeError(f"TEMPUS_LEDGER_INTEGRITY_FAILURE: {str(e)}")
                raise

            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": "Validation query completed.",
                "db_path": db_path,
                "result": output
            }, indent=2))]

        elif name == "tempus_list":
            db_path = validate_path(arguments.get("db", "tempus.db"))
            limit = arguments.get("limit", 10)
            offset = arguments.get("offset", 0)
            db = TempusDDB(db_path, "keys.json")
            output = db.list(limit=limit, offset=offset)
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": f"Listed {limit} decisions (offset {offset}).",
                "db_path": db_path,
                "decisions": json.loads(output) if isinstance(output, str) else output
            }, indent=2))]

        elif name == "tempus_export":
            db_path = validate_path(arguments.get("db", "tempus.db"))
            db = TempusDDB(db_path, "keys.json")
            output = db.export()
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": "Ledger exported successfully.",
                "db_path": db_path,
                "decisions": json.loads(output) if isinstance(output, str) else output
            }, indent=2))]

        elif name == "tempus_count":
            db_path = validate_path(arguments.get("db", "tempus.db"))
            db = TempusDDB(db_path, "keys.json")
            count = db.count()
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": f"Total decisions: {count}",
                "db_path": db_path,
                "total_decisions": count
            }, indent=2))]

        elif name == "tempus_cleanup":
            db_path = os.path.join(SANDBOX_DIR, "tempus.db")
            keys_path = os.path.join(SANDBOX_DIR, "keys.json")
            removed = []
            for p in [db_path, keys_path]:
                if os.path.exists(p):
                    os.remove(p)
                    removed.append(p)
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": "Cleanup successful.",
                "removed": removed
            }, indent=2))]

        else:
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "error": "TEMPUS_UNKNOWN_TOOL",
                "message": f"Unknown tool: {name}"
            }, indent=2))]

    except Exception as e:
        err_msg = str(e)
        error_code = "TEMPUS_EXECUTION_ERROR"
        for known_err in ["TEMPUS_LEDGER_INTEGRITY_FAILURE"]:
            if known_err in err_msg:
                error_code = known_err
                break

        return [TextContent(type="text", text=json.dumps({
            "status": "error",
            "error": error_code,
            "tool": name,
            "message": err_msg
        }, indent=2))]

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
