import argparse
import sys
import os
import json
from .mcp_server import main_sync
from ._tempus_ddb import TempusDDB, gen_keys

__version__ = "0.2.0-dev"  # update on releases

def run_init():
    keyfile = "keys.json"
    db_path = "tempus.db"

    if os.path.exists(keyfile):
        print(f"[{keyfile}] already exists — skipping key generation.")
    else:
        gen_keys(keyfile)
        print(f"✓ Generated new Ed25519 keys → {keyfile}")

    if os.path.exists(db_path):
        print(f"[{db_path}] already exists — verifying schema...")
    else:
        print(f"Initializing new ledger at {db_path}...")

    # The license is only used for the Rust core gate (MCP auto-generates valid one)
    db = TempusDDB("tmb_live_123_456", db_path, keyfile)
    print("✓ Tempus DDB ready.")
    print(f"  Keys:  {keyfile}")
    print(f"  DB:    {db_path}")

def run_verify():
    keyfile = "keys.json"
    db_path = "tempus.db"

    if not os.path.exists(db_path):
        print("No database found. Run 'tempus init' first.")
        return

    db = TempusDDB("tmb_live_123_456", db_path, keyfile if os.path.exists(keyfile) else "keys.json")
    try:
        result = db.validate()
        print("✓ Ledger validation successful.")
        print(result)
    except Exception as e:
        print(f"✗ Validation failed: {e}")

def run_record(args):
    """Direct CLI recording (task D improvement)."""
    keyfile = args.keyfile or "keys.json"
    db_path = args.db or "tempus.db"

    if not os.path.exists(keyfile):
        print("No keys found. Run 'tempus init' first.")
        sys.exit(1)

    try:
        payload = args.payload
        if payload and os.path.isfile(payload):
            with open(payload) as f:
                payload = f.read()
        rules = args.rules
        if rules and os.path.isfile(rules):
            with open(rules) as f:
                rules = f.read()

        if not payload or not rules:
            print("Error: --payload and --rules are required (or paths to JSON files).")
            sys.exit(1)

        db = TempusDDB("tmb_live_123_456", db_path, keyfile)

        result = db.record(
            payload=payload,
            rules=rules,
            genesis=args.genesis
        )
        print("✓ Decision recorded successfully.")
        print(result)
    except Exception as e:
        print(f"✗ Record failed: {e}")
        sys.exit(1)

def run_version():
    print(f"tempus {__version__}")

def main():
    parser = argparse.ArgumentParser(
        prog="tempus",
        description="Tempus DDB — The Tamper-Proof Flight Recorder for AI Agents"
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    subparsers = parser.add_subparsers(dest="command", required=False)

    # init
    subparsers.add_parser("init", help="Initialize keys and database")

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_cmd", required=True)
    mcp_sub.add_parser("start", help="Start the MCP server for agents (stdio)")

    # verify
    subparsers.add_parser("verify", help="Cryptographically verify the entire ledger")

    # record (new/improved for CLI users)
    record_p = subparsers.add_parser("record", help="Record a decision directly from CLI")
    record_p.add_argument("--db", default="tempus.db", help="Path to the ledger database")
    record_p.add_argument("--keyfile", default="keys.json", help="Path to Ed25519 key file")
    record_p.add_argument("--payload", required=True, help="JSON string or path to JSON file with the decision")
    record_p.add_argument("--rules", required=True, help="JSON string or path to JSON file with the rules applied")
    record_p.add_argument("--genesis", action="store_true", help="Mark this as the first decision in the chain")

    args = parser.parse_args()

    if getattr(args, "version", False):
        run_version()
        return

    if args.command == "init":
        run_init()
    elif args.command == "mcp" and getattr(args, "mcp_cmd", None) == "start":
        main_sync()
    elif args.command == "verify":
        run_verify()
    elif args.command == "record":
        run_record(args)
    elif args.command is None:
        parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
