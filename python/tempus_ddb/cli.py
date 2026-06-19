import argparse
import sys
import os
import subprocess
import asyncio
import json
from .mcp_server import main_sync
from ._tempus_ddb import TempusDDB, gen_keys

def run_init():
    keyfile = "b2a_keys.json"
    if os.path.exists(keyfile):
        print(f"[{keyfile}] already exists. Skipping key generation.")
    else:
        gen_keys(keyfile)
        print(f"Generated new keys at {keyfile}")
        
    db_path = "b2a_agent.db"
    if os.path.exists(db_path):
        print(f"[{db_path}] already exists. Verifying...")
    else:
        print(f"Initializing database at {db_path}...")
    
    db = TempusDDB("tmb_live_123_456", db_path, keyfile)
    print("Init complete.")

def run_verify():
    keyfile = "b2a_keys.json"
    db_path = "b2a_agent.db"
    if not os.path.exists(db_path):
        print("Database not found. Run 'tempus init' first.")
        return
    db = TempusDDB("tmb_live_123_456", db_path, keyfile if os.path.exists(keyfile) else "keys.json")
    try:
        output = db.validate()
        print(output)
    except Exception as e:
        print(f"Verification error: {e}")

def run_demo():
    # Execute the demo_agent_b2a script using the python executable
    script = os.path.join(os.getcwd(), "demo_agent_b2a.py")
    if not os.path.exists(script):
        # Fallback if installed globally: the script might not be here.
        print("Please run this command from the Tempus DDB repository root.")
        sys.exit(1)
    subprocess.run([sys.executable, script])

def run_test():
    script = os.path.join(os.getcwd(), "test_b2a_suite.py")
    if not os.path.exists(script):
        print("Please run this command from the Tempus DDB repository root.")
        sys.exit(1)
    subprocess.run([sys.executable, script])

def main():
    parser = argparse.ArgumentParser(prog="tempus", description="Tempus DDB B2A CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("init", help="Initialize local agent files without overwriting")
    
    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_cmd", required=True)
    mcp_sub.add_parser("start", help="Start the MCP server")
    
    demo_parser = subparsers.add_parser("demo", help="Run demos")
    demo_sub = demo_parser.add_subparsers(dest="demo_cmd", required=True)
    demo_sub.add_parser("b2a", help="Run the B2A demo")
    
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_sub = test_parser.add_subparsers(dest="test_cmd", required=True)
    test_sub.add_parser("b2a", help="Run the B2A test suite")
    
    subparsers.add_parser("verify", help="Verify the local ledger integrity")
    
    args = parser.parse_args()
    
    if args.command == "init":
        run_init()
    elif args.command == "mcp" and args.mcp_cmd == "start":
        main_sync()
    elif args.command == "demo" and args.demo_cmd == "b2a":
        run_demo()
    elif args.command == "test" and args.test_cmd == "b2a":
        run_test()
    elif args.command == "verify":
        run_verify()

if __name__ == "__main__":
    main()
