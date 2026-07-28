"""
Tempus DDB - The Tamper-Evident Flight Recorder for AI Agents

This package provides a cryptographically secure, tamper-evident ledger for recording
critical decisions made by autonomous AI agents.

Core Components:
- TempusDDB: Main class for interacting with the decision ledger.
- gen_keys: Utility to generate Ed25519 key pairs.
- main_sync: Entry point for the MCP server.

Typical usage:
    from tempus_ddb import TempusDDB, gen_keys

    gen_keys("keys.json")
    db = TempusDDB("tempus.db", "keys.json")
    db.record(payload, rules, genesis=True)
"""

from ._tempus_ddb import TempusDDB, gen_keys, TempusExecutor
from .mcp_server import main_sync

__all__ = ["TempusDDB", "gen_keys", "TempusExecutor", "main_sync"]
