# Tempus DDB: The Decision Database for Autonomous Agents

Tempus DDB is a decentralized, immutable decision ledger designed specifically for autonomous AI agents. Built on Rust and SQLite with Ed25519 cryptography, it allows agents to create an auditable, tamper-proof "Flight Recorder" of their actions, decisions, and reasoning.

## Key Features

1. **Cryptographic Proof-of-Decision**: Every action is hashed and signed, creating an immutable causal chain.
2. **High Performance**: Rust core with SQLite backend ensures lightning-fast local operations.
3. **Agent-Native (B2A)**: Built with the Model Context Protocol (MCP) in mind. It exposes standard tools for agents to integrate dynamically.
4. **Autonomous Monetization**: Includes a simulated smart-contract paywall. Agents must autonomously learn to fund their wallets to record decisions, enforcing a "Crypto Tollbooth" dynamic.

## Architecture

- **Core Engine (Rust)**: Handles cryptographic signing, hashing, database initialization, and ledger validation.
- **MCP Server (Python)**: Acts as the integration layer. Exposes tools like `tempus_record` and `tempus_validate`. Handles the crypto paywall simulation and errors.
- **Agent Instructions**: Self-healing documentation (`AGENT_INSTRUCTIONS.md`) designed to be read by LLMs to learn how to bypass the paywall autonomously.

## Getting Started

Agents can connect to the MCP server directly using stdio:
```bash
python mcp_server.py
```

For detailed agent instructions, refer to `AGENT_INSTRUCTIONS.md`.
