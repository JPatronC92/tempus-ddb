<p align="center">
  <img src="assets/logo.png" alt="Tempus DDB Logo" width="220">
</p>

<h1 align="center">Tempus DDB</h1>

<p align="center">
  <strong>The Tamper-Proof Flight Recorder for AI Agents</strong><br>
  <sub>Local-first • Cryptographically verifiable • Built for MCP</sub>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#why-tempus-ddb">Why Tempus DDB</a> •
  <a href="#usage-examples">Examples</a> •
  <a href="#cli-reference">CLI</a> •
  <a href="#mcp-tools">MCP Tools</a> •
  <a href="#roadmap">Roadmap</a>
</p>

---

## What is Tempus DDB?

**Tempus DDB** is a **free, local-first, cryptographically secure decision ledger** for autonomous AI agents and agentic systems.

It functions as an **immutable Flight Recorder**: agents can record critical decisions with Ed25519 digital signatures and a hash-chained causal structure. This produces a tamper-proof audit trail that can be independently verified at any time.

### Official One-Liner
> Give your AI agents a memory they cannot rewrite.

### Core Value Proposition
- **Verifiability first**: Every decision is signed and linked — alterations are immediately detectable.
- **Built for agents**: Native support for MCP (Model Context Protocol), making it trivial to integrate with Claude, Cursor, LangGraph, CrewAI, etc.
- **Zero friction**: Completely free, offline by default, no accounts or cloud required.
- **Production-grade simplicity**: Small Rust core + clean Python bindings. One binary. One database.

### Positioning
Tempus DDB is the minimal, trustworthy foundation for any system where autonomous agents must be accountable for high-stakes actions.

---

## Why Use Tempus DDB?

AI agents are increasingly making high-impact decisions. Without a reliable audit trail, it's impossible to know:

- What the agent decided
- When it decided
- Based on what rules or data
- Whether the record was later altered

**Tempus DDB solves this** by giving agents a simple, reliable way to sign and chain their decisions.

### Ideal Use Cases
- Financial or budget-related actions
- Code generation or modification with external effects
- Configuration changes and permission grants
- Strategic or business-critical decisions
- Multi-agent coordination and accountability
- Compliance, debugging, or post-incident analysis

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/JPatronC92/tempus-ddb.git
cd tempus-ddb
pip install .
```

### 2. Initialize

```bash
tempus init
```

This creates:
- `keys.json` — Your Ed25519 keypair
- `tempus.db` — The decision ledger

### 3. Use with Claude / MCP Clients

Add to your MCP configuration:

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

### 4. Record a Decision (via agent or CLI)

Agents can call `tempus_record_decision` (or the alias `tempus_record`).

Example payload:
```json
{
  "action": "approve_budget",
  "amount": 12500,
  "reason": "Q3 marketing campaign",
  "risks": ["market volatility"]
}
```

Rules (the logic the agent applied):
```json
{
  "max_amount": 15000,
  "requires_approval": true
}
```

---

## How the Causal Chain Works

Every record contains:
- A canonical hash of (parent_hash + timestamp + payload + rules)
- An Ed25519 signature over that hash
- The actor's public key (derived from the keyfile)

```
Genesis (no parent)
   ↓
Decision 1  ← signed hash includes genesis hash
   ↓
Decision 2  ← signed hash includes Decision 1 hash
   ↓
...
```

Running `tempus_validate` replays the entire chain and checks every signature and hash link.

---

## CLI Reference & Improvements (Work in Progress)

Current commands:

```bash
tempus init          # Bootstrap keys + database
tempus mcp start     # Launch MCP server for agents
tempus verify        # Full cryptographic validation
```

We are improving the CLI right now (task D). Planned / in-progress:

- `tempus record` — direct CLI recording (payload + rules from file or stdin)
- `tempus version`
- `tempus status` — show last record, key info, etc.
- Nicer colored output and better error messages

See the CLI source for latest or run `tempus --help`.

---

## MCP Tools Reference

| Tool                    | Description                                           | Key Parameters                              |
|-------------------------|-------------------------------------------------------|---------------------------------------------|
| `tempus_init`           | Initialize SQLite ledger                              | `db`                                        |
| `tempus_gen_keys`       | Generate Ed25519 signing keys                         | `output`                                    |
| `tempus_record`         | Record decision (alias)                               | `db`, `payload`, `rules`, `keyfile`         |
| `tempus_record_decision`| Main tool to log a decision                           | + `genesis`, `parent`, `idempotency_key`    |
| `tempus_validate`       | Verify the full immutable chain                       | `db`                                        |
| `tempus_cleanup`        | Wipe local files (useful for demos)                   | —                                           |

---

## Security Model

- Only the holder of the private key in `keyfile` can create valid signed records.
- Hash chaining + signatures → any modification is immediately detectable.
- Fully local by default — nothing leaves the machine.
- The license gate in the Rust core is satisfied automatically by the MCP layer for local use.

---

## Roadmap

See the complete **executable roadmap** in [ROADMAP.md](ROADMAP.md).

Current sprint focus: A + B + D (product definition, docs, CLI + examples) as requested.

---

## Contributing

We welcome contributions that keep the core simple and focused.

1. Fork the repo
2. Make changes on a feature branch
3. Ensure tests pass (`python -m pytest` or the existing integration tests)
4. Open a PR

---

**Tempus DDB** — Give your agents a memory they can't rewrite.
