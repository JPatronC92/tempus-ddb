# Tempus DDB: Tamper-Proof Decision Ledger for AI Agents

Tempus DDB is a lightweight, immutable decision ledger for autonomous AI agents. Built in Rust + SQLite with Ed25519 cryptography, it lets agents create a cryptographically verifiable audit trail ("Flight Recorder") of their critical decisions and actions.

## Key Features

1. **Cryptographic Proof-of-Decision** — Every record is hashed and signed, forming an immutable causal chain.
2. **High Performance** — Rust core + SQLite. Extremely fast for local use.
3. **Agent-Native (MCP)** — Exposes clean tools via the Model Context Protocol so agents (Claude, etc.) can use it directly.
4. **Simple & Free** — No paywalls. Just initialize, generate keys, and record decisions.

## Architecture

- **Core Engine (Rust)**: Cryptographic signing, hashing, SQLite storage and ledger validation.
- **MCP Server (Python)**: Thin integration layer exposing `tempus_record`, `tempus_validate`, etc.
- Fully self-contained. No external services required.

## Getting Started (CLI)

### Installation

```bash
git clone https://github.com/JPatronC92/tempus-ddb.git
cd tempus-ddb
pip install .
```

### Quick Start

```bash
# 1. Initialize (creates keys + db)
tempus init

# 2. Start the MCP server (for Claude Desktop / MCP clients)
tempus mcp start
```

### Verify the ledger

```bash
tempus verify
```

### MCP Client Configuration (Claude Desktop, etc.)

```json
{
  "mcpServers": {
    "tempus-ddb": {
      "command": "tempus",
      "args": ["mcp", "start"]
    }
  }
}
```

## Core Tools (MCP)

- `tempus_init` — Initialize the database
- `tempus_gen_keys` — Generate Ed25519 keypair
- `tempus_record` / `tempus_record_decision` — Record an immutable decision
- `tempus_validate` — Verify the entire causal chain
- `tempus_cleanup` — Reset local files

## When to use it

Use Tempus DDB before executing high-stakes actions:
- Financial transactions or budget approvals
- Code changes with external access
- Configuration or permission changes
- Strategic business decisions

## Roadmap

- [x] Core Rust engine + Ed25519 + SQLite causal ledger
- [x] MCP integration (free, no paywall)
- [ ] Cloud synchronization & aggregation
- [ ] Multi-agent consensus
- [ ] Optional on-chain notarization (future)
