import argparse
import sys
import os
import json
from .mcp_server import main_sync
from ._tempus_ddb import TempusDDB, gen_keys
import hashlib
import hmac
import secrets
import string

__version__ = "0.2.0-dev"  # update on releases


def _get_cli_license() -> str:
    """Generate a valid license key for direct CLI usage (exact same as MCP server)."""
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(24))
    hmac_sig = hmac.new(
        b"tempus-ddb-hmac-secret-key-v1-2026",
        random_part.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"tmb_live_{random_part}_{hmac_sig}"


CLI_LICENSE = _get_cli_license()

def run_init():
    keyfile = "keys.json"
    db_path = "tempus.db"

    if os.path.exists(keyfile):
        print(f"[{keyfile}] already exists — skipping key generation.")
    else:
        try:
            gen_keys(keyfile)
            print(f"✓ Generated new Ed25519 keys → {keyfile}")
        except Exception as e:
            print(f"✗ Failed to generate keys: {e}")
            sys.exit(1)

    if os.path.exists(db_path):
        print(f"[{db_path}] already exists — verifying schema...")
    else:
        print(f"Initializing new ledger at {db_path}...")

    try:
        db = TempusDDB(CLI_LICENSE, db_path, keyfile)
        print("✓ Tempus DDB ready.")
        print(f"  Keys:  {keyfile}")
        print(f"  DB:    {db_path}")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        sys.exit(1)

def run_verify():
    keyfile = "keys.json"
    db_path = "tempus.db"

    if not os.path.exists(db_path):
        print("✗ No database found. Run 'tempus init' first.")
        sys.exit(1)

    try:
        db = TempusDDB(CLI_LICENSE, db_path, keyfile if os.path.exists(keyfile) else "keys.json")
        result = db.validate()
        result_str = str(result).lower()
        if "invalid" in result_str or "error" in result_str or "mismatch" in result_str:
            print("✗ Ledger validation FAILED")
            print(result)
            sys.exit(1)
        else:
            print("✓ Ledger validation successful.")
            print(result)
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        sys.exit(1)


def run_status():
    keyfile = "keys.json"
    db_path = "tempus.db"

    print("Tempus DDB Status")
    print("=================")

    # Keys
    if os.path.exists(keyfile):
        try:
            size = os.path.getsize(keyfile)
            print(f"✓ Keys file: {keyfile} ({size} bytes)")
        except Exception:
            print(f"✓ Keys file: {keyfile}")
    else:
        print("✗ Keys file: not found (run 'tempus init')")

    # Database
    if os.path.exists(db_path):
        try:
            size = os.path.getsize(db_path)
            print(f"✓ Database: {db_path} ({size} bytes)")
        except Exception:
            print(f"✓ Database: {db_path}")

        try:
            db = TempusDDB(CLI_LICENSE, db_path, keyfile if os.path.exists(keyfile) else "keys.json")
            validation = db.validate()
            val_str = str(validation).lower()

            if "invalid" in val_str or "error" in val_str or "mismatch" in val_str:
                print("✗ Chain integrity: INVALID")
                print(f"  Details: {validation}")
            else:
                print("✓ Chain integrity: VALID")

            # Try to show last hash if present in result
            try:
                if isinstance(validation, str):
                    data = json.loads(validation)
                else:
                    data = validation
                if isinstance(data, dict):
                    last_hash = data.get("latest_hash") or data.get("result", {}).get("latest_hash")
                    if last_hash:
                        print(f"  Latest hash: {last_hash}")
            except Exception:
                pass

        except Exception as e:
            print(f"✗ Could not validate database: {e}")
    else:
        print("✗ Database: not found (run 'tempus init' and record at least once)")

    print("\nNext steps if needed:")
    print("  tempus init     # to initialize")
    print("  tempus record   # to record a decision")

def run_record(args):
    """Direct CLI recording (task D improvement)."""
    keyfile = args.keyfile or "keys.json"
    db_path = args.db or "tempus.db"

    if not os.path.exists(keyfile):
        print("✗ No keys found. Run 'tempus init' first.")
        sys.exit(1)

    if not os.path.exists(db_path) and not args.genesis:
        # For non-genesis, db should exist
        print("✗ Database not found. You must create the first (genesis) record first.")
        sys.exit(1)

    try:
        # Load payload
        payload = args.payload
        if os.path.isfile(payload):
            with open(payload, encoding="utf-8") as f:
                payload = f.read().strip()
        try:
            json.loads(payload)
        except json.JSONDecodeError:
            print("✗ --payload must be valid JSON (or path to JSON file)")
            sys.exit(1)

        # Load rules
        rules = args.rules
        if os.path.isfile(rules):
            with open(rules, encoding="utf-8") as f:
                rules = f.read().strip()
        try:
            json.loads(rules)
        except json.JSONDecodeError:
            print("✗ --rules must be valid JSON (or path to JSON file)")
            sys.exit(1)

        # Validation for chaining
        if not args.genesis and not args.parent:
            print("✗ Non-genesis records require --parent <hash> (get it from previous record result or 'tempus status')")
            sys.exit(1)

        db = TempusDDB(CLI_LICENSE, db_path, keyfile)

        # Note: The Rust binding only supports `genesis`. Logical parent chaining
        # should be included in the `payload` if needed for audit purposes.
        result = db.record(payload, rules, genesis=args.genesis)
        print("✓ Decision recorded successfully.")
        print(result)
    except Exception as e:
        err_msg = str(e)
        if "parent" in err_msg.lower() or "genesis" in err_msg.lower():
            print(f"✗ Chaining error: {err_msg}")
            print("  Tip: Use --genesis for the first record, or provide --parent with the previous hash.")
        else:
            print(f"✗ Record failed: {err_msg}")
        sys.exit(1)

def run_version():
    print(f"tempus {__version__}")

def main():
    parser = argparse.ArgumentParser(
        prog="tempus",
        description="Tempus DDB — The Tamper-Proof Flight Recorder for AI Agents"
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit"
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    # init
    subparsers.add_parser("init", help="Initialize keys and database")

    # mcp
    mcp_parser = subparsers.add_parser("mcp", help="MCP server commands")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_cmd", required=True)
    mcp_sub.add_parser("start", help="Start the MCP server for agents (stdio)")

    # verify
    subparsers.add_parser("verify", help="Cryptographically verify the entire ledger")

    # status
    subparsers.add_parser("status", help="Show current ledger and keys status")

    # record (new/improved for CLI users)
    record_p = subparsers.add_parser("record", help="Record a decision directly from CLI")
    record_p.add_argument("--db", default="tempus.db", help="Path to the ledger database")
    record_p.add_argument("--keyfile", default="keys.json", help="Path to Ed25519 key file")
    record_p.add_argument("--payload", required=True, help="JSON string or path to JSON file with the decision")
    record_p.add_argument("--rules", required=True, help="JSON string or path to JSON file with the rules applied")
    record_p.add_argument("--genesis", action="store_true", help="Mark this as the first decision in the chain")
    # Note: Parent chaining for audit should be included inside the JSON payload.
    # The core ledger is append-only controlled by the `genesis` flag.

    args = parser.parse_args()

    if getattr(args, "version", False):
        run_version()
        return

    try:
        if args.command == "init":
            run_init()
        elif args.command == "mcp" and getattr(args, "mcp_cmd", None) == "start":
            main_sync()
        elif args.command == "verify":
            run_verify()
        elif args.command == "status":
            run_status()
        elif args.command == "record":
            run_record(args)
        elif args.command is None:
            parser.print_help()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
    except Exception as e:
        # Last resort - should not reach here for handled cases
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
