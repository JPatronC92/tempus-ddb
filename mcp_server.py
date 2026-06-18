import asyncio
import json
import os
import subprocess
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Configuracion global
BIN_PATH = "/data/data/com.termux/files/home/tempus-ddb/target/debug/tempus-ddb"
WALLET_FILE = "agent_wallet.json"
COST_PER_RECORD = 0.01

def load_wallet():
    if not os.path.exists(WALLET_FILE):
        return {"balance_usdc": 0.0}
    with open(WALLET_FILE, "r") as f:
        return json.load(f)

def save_wallet(wallet):
    with open(WALLET_FILE, "w") as f:
        json.dump(wallet, f, indent=2)

def run_cmd(args):
    cmd = [BIN_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando {' '.join(args)}:\n{result.stderr}")
    return result.stdout.strip()

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
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "tempus_init":
            db = arguments.get("db", "tempus_ddb.db")
            output = run_cmd(["init", "--db", db])
            return [TextContent(type="text", text=f"Database initialized: {db}")]
            
        elif name == "tempus_gen_keys":
            output_file = arguments.get("output", "keys.json")
            output = run_cmd(["gen-keys", "--output", output_file])
            return [TextContent(type="text", text=f"Keys generated at {output_file}:\n{output}")]
            
        elif name == "tempus_record":
            wallet = load_wallet()
            if wallet["balance_usdc"] < COST_PER_RECORD:
                error_response = {
                    "error": "insufficient_funds",
                    "action_required": "send_crypto",
                    "amount": COST_PER_RECORD,
                    "currency": "USDC",
                    "wallet_address": "0xTEMPUSAGENTWALLET123456",
                    "message": "You must fund your wallet using the 'tempus_fund_wallet' tool before calling 'tempus_record'."
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2))]
            
            db = arguments["db"]
            payload = arguments["payload"]
            rules = arguments["rules"]
            keyfile = arguments["keyfile"]
            
            args_list = ["record", "--db", db, "--payload", payload, "--rules", rules, "--keyfile", keyfile]
            if arguments.get("parent"):
                args_list.extend(["--parent", arguments["parent"]])
            if arguments.get("genesis"):
                args_list.append("--genesis")
                
            output = run_cmd(args_list)
            
            # Deduct funds
            wallet["balance_usdc"] -= COST_PER_RECORD
            save_wallet(wallet)
            
            return [TextContent(type="text", text=f"Record successful. Remaining balance: {wallet['balance_usdc']:.2f} USDC.\nOutput:\n{output}")]
            
        elif name == "tempus_validate":
            db = arguments.get("db", "tempus_ddb.db")
            output = run_cmd(["validate", "--db", db])
            return [TextContent(type="text", text=output)]
            
        elif name == "tempus_fund_wallet":
            amount = arguments["amount"]
            wallet = load_wallet()
            wallet["balance_usdc"] += float(amount)
            save_wallet(wallet)
            return [TextContent(type="text", text=f"Wallet successfully funded with {amount} USDC. New balance: {wallet['balance_usdc']:.2f} USDC.")]
            
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
