import argparse
import sys
import os
import json
from .mcp_server import main_sync
from ._tempus_ddb import TempusDDB, gen_keys
import importlib.metadata

try:
    __version__ = importlib.metadata.version("tempus_ddb")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

# --- Default paths (used when global args are not provided) ---
DEFAULT_KEYFILE = "keys.json"
DEFAULT_DB = "tempus.db"


def _resolve_paths(args):
    """Extract db and keyfile paths from global args, falling back to defaults."""
    db = getattr(args, "db", None) or DEFAULT_DB
    keyfile = getattr(args, "keyfile", None) or DEFAULT_KEYFILE
    return db, keyfile


def run_init(args):
    db_path, keyfile = _resolve_paths(args)

    if os.path.exists(keyfile):
        print(f"[{keyfile}] already exists — skipping key generation.")
    else:
        try:
            gen_keys(keyfile)
            print(f"✓ Generated new Ed25519 keys → {keyfile}")
        except Exception as e:
            print(f"✗ Failed to generate keys: {e}", file=sys.stderr)
            sys.exit(1)

    if os.path.exists(db_path):
        print(f"[{db_path}] already exists — verifying schema...")
    else:
        print(f"Initializing new ledger at {db_path}...")

    try:
        db = TempusDDB(db_path, keyfile)
        print("✓ Tempus DDB ready.")
        print(f"  Keys:  {keyfile}")
        print(f"  DB:    {db_path}")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}", file=sys.stderr)
        sys.exit(1)

def run_verify(args):
    db_path, keyfile = _resolve_paths(args)

    if not os.path.exists(db_path):
        print("✗ No database found. Run 'tempus init' first.", file=sys.stderr)
        sys.exit(1)

    try:
        db = TempusDDB(db_path, keyfile if os.path.exists(keyfile) else DEFAULT_KEYFILE)
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
        print(f"✗ Validation failed: {e}", file=sys.stderr)
        sys.exit(1)


def run_status(args):
    db_path, keyfile = _resolve_paths(args)

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
            db = TempusDDB(db_path, keyfile if os.path.exists(keyfile) else DEFAULT_KEYFILE)
            validation = db.validate()
            val_str = str(validation).lower()

            if "invalid" in val_str or "error" in val_str or "mismatch" in val_str:
                print("✗ Chain integrity: INVALID")
                print(f"  Details: {validation}")
            else:
                print("✓ Chain integrity: VALID")

            # Show record count
            try:
                count = db.count()
                print(f"  Total decisions: {count}")
            except Exception:
                pass

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
    db_path, keyfile = _resolve_paths(args)

    if not os.path.exists(keyfile):
        print("✗ No keys found. Run 'tempus init' first.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(db_path) and not args.genesis:
        # For non-genesis, db should exist
        print("✗ Database not found. You must create the first (genesis) record first.", file=sys.stderr)
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
            print("✗ --payload must be valid JSON (or path to JSON file)", file=sys.stderr)
            sys.exit(1)

        # Load rules
        rules = args.rules
        if os.path.isfile(rules):
            with open(rules, encoding="utf-8") as f:
                rules = f.read().strip()
        try:
            json.loads(rules)
        except json.JSONDecodeError:
            print("✗ --rules must be valid JSON (or path to JSON file)", file=sys.stderr)
            sys.exit(1)

        db = TempusDDB(db_path, keyfile)

        # The core auto-links non-genesis records to the latest record.
        result = db.record(payload, rules, genesis=args.genesis)
        print("✓ Decision recorded successfully.")
        print(result)
    except Exception as e:
        err_msg = str(e)
        if "genesis" in err_msg.lower() or "empty" in err_msg.lower():
            print(f"✗ Chaining error: {err_msg}", file=sys.stderr)
            print("  Tip: Use --genesis only for the first record. Later records auto-link to the latest record.", file=sys.stderr)
        else:
            print(f"✗ Record failed: {err_msg}", file=sys.stderr)
        sys.exit(1)


def run_export(args):
    """Export the entire ledger as a JSON array."""
    db_path, keyfile = _resolve_paths(args)

    if not os.path.exists(db_path):
        print("✗ No database found. Run 'tempus init' first.", file=sys.stderr)
        sys.exit(1)

    try:
        db = TempusDDB(db_path, keyfile if os.path.exists(keyfile) else DEFAULT_KEYFILE)
        result = db.export()
        print(result)
    except Exception as e:
        print(f"✗ Export failed: {e}", file=sys.stderr)
        sys.exit(1)


def run_list(args):
    """List decisions with pagination."""
    db_path, keyfile = _resolve_paths(args)

    if not os.path.exists(db_path):
        print("✗ No database found. Run 'tempus init' first.", file=sys.stderr)
        sys.exit(1)

    try:
        db = TempusDDB(db_path, keyfile if os.path.exists(keyfile) else DEFAULT_KEYFILE)
        result = db.list(limit=args.limit, offset=args.offset)
        # Pretty-print the JSON output
        try:
            parsed = json.loads(result)
            print(json.dumps(parsed, indent=2))
        except (json.JSONDecodeError, TypeError):
            print(result)
    except Exception as e:
        print(f"✗ List failed: {e}", file=sys.stderr)
        sys.exit(1)


def run_count(args):
    """Count the total number of decisions in the ledger."""
    db_path, keyfile = _resolve_paths(args)

    if not os.path.exists(db_path):
        print("✗ No database found. Run 'tempus init' first.", file=sys.stderr)
        sys.exit(1)

    try:
        db = TempusDDB(db_path, keyfile if os.path.exists(keyfile) else DEFAULT_KEYFILE)
        count = db.count()
        print(json.dumps({"total_decisions": count}))
    except Exception as e:
        print(f"✗ Count failed: {e}", file=sys.stderr)
        sys.exit(1)


def run_version():
    print(f"tempus {__version__}")

def main():
    parser = argparse.ArgumentParser(
        prog="tempus",
        description="Tempus DDB — The Tamper-Evident Flight Recorder for AI Agents"
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit"
    )
    # Global arguments available to all subcommands
    parser.add_argument(
        "--db", default=DEFAULT_DB,
        help=f"Path to the ledger database (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--keyfile", default=DEFAULT_KEYFILE,
        help=f"Path to the Ed25519 key file (default: {DEFAULT_KEYFILE})"
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
    record_p.add_argument("--payload", required=True, help="JSON string or path to JSON file with the decision")
    record_p.add_argument("--rules", required=True, help="JSON string or path to JSON file with the rules applied")
    record_p.add_argument("--genesis", action="store_true", help="Mark this as the first decision in the chain")
    # Note: Parent chaining for audit should be included inside the JSON payload.
    # The core ledger is append-only controlled by the `genesis` flag.

    # export
    subparsers.add_parser("export", help="Export the entire ledger as a JSON array")

    # list
    list_p = subparsers.add_parser("list", help="List decisions with pagination")
    list_p.add_argument("--limit", type=int, default=10, help="Maximum number of records to return (default: 10)")
    list_p.add_argument("--offset", type=int, default=0, help="Number of records to skip (default: 0)")

    # count
    subparsers.add_parser("count", help="Count the total number of decisions in the ledger")

    args = parser.parse_args()

    if getattr(args, "version", False):
        run_version()
        return

    try:
        if args.command == "init":
            run_init(args)
        elif args.command == "mcp" and getattr(args, "mcp_cmd", None) == "start":
            main_sync()
        elif args.command == "verify":
            run_verify(args)
        elif args.command == "status":
            run_status(args)
        elif args.command == "record":
            run_record(args)
        elif args.command == "export":
            run_export(args)
        elif args.command == "list":
            run_list(args)
        elif args.command == "count":
            run_count(args)
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
