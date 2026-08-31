"""
Tempus DDB - The B2A security gate for autonomous agent actions.

This package issues signed, single-use permits before autonomous effects and records
tamper-evident execution receipts. The legacy decision ledger remains available for
compatibility, but is not an enforcement boundary.

Core Components:
- TempusDDB: Gate, receipt store, and legacy-ledger compatibility API.
- TempusExecutor: Generic permit verifier and single-consumption helper for adapters.
- GitHubExecutorAdapter: Credential-isolated executor for bound GitHub writes.
- gen_keys: Utility to generate Ed25519 key pairs.
- main_sync: Entry point for the MCP server.

Typical usage:
    from tempus_ddb import TempusDDB, gen_keys

    gen_keys("keys.json")
    gate = TempusDDB("tempus.db", "keys.json")
    # Register identities, submit a signed action intent, then verify the receipt.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tempus-ddb")
except PackageNotFoundError:
    try:
        __version__ = version("tempus_ddb")
    except PackageNotFoundError:
        __version__ = "0.4.0"

from ._tempus_ddb import TempusDDB, TempusExecutor, gen_keys
from .github_executor import GitHubExecutorAdapter, UnknownExecutionError
from .mcp_server import main_sync

__all__ = [
    "GitHubExecutorAdapter",
    "TempusDDB",
    "TempusExecutor",
    "UnknownExecutionError",
    "__version__",
    "gen_keys",
    "main_sync",
]
