import argparse
import sys
import os
import subprocess
from .mcp_server import main_sync
from ._tempus_ddb import TempusDDB, gen_keys

def run_init():
    keyfile = "keys.json"
    if os.path.exists(keyfile):
        print(f"[{keyfile}] already exists. Skipping key generation.")
    else:
        gen_keys(keyfile)
        print(f"Generated new keys at {keyfile}")
        
    db_path = "tempus.db"
    if os.path.exists(db_path):
        print(f"[{db_path}] already exists. Verifying...")
    else:
        print(f"Initializing database at {db_path}...")
    
    # Use a valid license (generated internally in mcp too)
    db = TempusDDB("tmb_live_123_456", db_path, keyfile)
    print("Init complete.")

def run_verify():
    keyfile = "keys.json"
    db_path = "tempus.db"
    if not os.path.exists(db_path):
        print("Database not found. Run 'tempus init' first.")
        return
    db = TempusDDB("tmb_live_123_456", db_path, keyfile if os.path.exists(keyfile) else "keys.json")
    try:
        output = db.validate()
        print(output)
    except Exception as e:
        print(f"Verification error: {e}")

def main():
    parser = argparse.ArgumentParser(prog="tempus", description="Tempus DDB - Tamper-proof decision ledger for agents")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("init", help="Initialize local database and keys")
    
    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_cmd", required=True)
    mcp_sub.add_parser("start", help="Start the MCP server (for Claude / MCP clients)")
    
    subparsers.add_parser("verify", help="Verify the local ledger integrity")
    
    args = parser.parse_args()
    
    if args.command == "init":
        run_init()
    elif args.command == "mcp" and args.mcp_cmd == "start":
        main_sync()
    elif args.command == "verify":
        run_verify()

if __name__ == "__main__":
    main()
