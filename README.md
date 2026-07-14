<p align="center">
  <img src="assets/logo.png" alt="Tempus DDB Logo" width="220">
</p>

<h1 align="center">Tempus DDB</h1>

<p align="center">
  <strong>The Tamper-Evident Flight Recorder for AI Agents</strong><br>
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

**Tempus DDB** is a **free, local-first, offline-by-default, cryptographically verifiable decision ledger** for autonomous AI agents and agentic systems.

It functions as a **tamper-evident Flight Recorder**: agents can record critical decisions with Ed25519 digital signatures and a hash-chained causal structure. This produces a tamper-evident audit trail that can be independently verified at any time.

### Official One-Liner
> Give your AI agents a memory they cannot rewrite.

### Core Value Proposition
- **Verifiability first**: Every decision is signed and linked — alterations are immediately detectable.
- **Built for agents**: Native support for MCP (Model Context Protocol), making it trivial to integrate with Claude, Cursor, LangGraph, CrewAI, etc.
- **Zero friction**: Completely free, offline by default, no accounts, no cloud required, and no license gate.
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

## CLI Reference

### Official Python CLI (`tempus`)
The primary interface for developers and users. Installed via `pip install tempus_ddb`.

```bash
tempus init          # Bootstrap keys + database
tempus mcp start     # Launch MCP server for agents (stdio)
tempus verify        # Full cryptographic validation
tempus status        # Show keys, DB and chain status
tempus record        # Record a decision directly from CLI
tempus --version     # Show version
```

Example of direct record:

```bash
tempus record \
  --payload '{"action": "update_config", "key": "timeout", "value": 30}' \
  --rules '{"max_value": 300}' \
  --genesis
```

### Internal Core CLI (`tempus-ddb`)
If you build the Rust core directly (`cargo build`), you will get an internal binary `tempus-ddb`. This is mostly a thin wrapper for development, debugging, and the `tamper_demo_rust_cli.py` stress test. For production usage, always use the `tempus` Python CLI or the TempusDDB class directly.

---

## Tamper Detection Demo

You can run the interactive tamper detection test to see how the ledger catches malicious manipulation:

```bash
python tamper_demo_rust_cli.py
```
This script creates a valid causal chain of 50 records, directly modifies a payload via SQLite without updating the cryptographic hash or signature, and then proves that Tempus DDB immediately catches the breach.

---

## MCP Tools Reference

| Tool                    | Description                                           | Key Parameters                              |
|-------------------------|-------------------------------------------------------|---------------------------------------------|
| `tempus_init`           | Initialize SQLite ledger                              | `db`                                        |
| `tempus_gen_keys`       | Generate Ed25519 signing keys                         | `output`                                    |
| `tempus_record`         | Record decision (alias)                               | `db`, `payload`, `rules`, `keyfile`         |
| `tempus_record_decision`| Main tool to log a decision                           | `db`, `payload`, `rules`, `keyfile`, `genesis` |
| `tempus_validate`       | Verify the full tamper-evident chain                  | `db`                                        |
| `tempus_cleanup`        | Wipe local files (useful for demos)                   | —                                           |

---

## Security Model

- Only the holder of the private key in `keyfile` can create valid signed records.
- **⚠️ WARNING:** Your `keyfile` (e.g., `keys.json`) contains the raw Ed25519 private key. **Do not commit this file to version control**. Exposing it completely compromises the integrity of the ledger, allowing an attacker to forge records.
- Hash chaining + signatures → any modification is immediately detectable.
- Fully local by default — nothing leaves the machine.
- The core has no license gate. It is fully open.

---

## Commercial Opportunities & Business Models

While Tempus DDB core is free, open-source, and local-first, the architecture naturally supports highly profitable enterprise scaling models:

### 1. Tempus Cloud (Multi-Agent Sync & Backup)
Local ledgers (`tempus.db`) are great for single agents, but enterprise deployments with hundreds of autonomous agents need consolidation. Tempus Cloud is a premium SaaS that synchronizes, backs up, and aggregates local ledgers into a secure, centralized vault for real-time observability and cross-agent consensus.

### 2. Cryptographic Anchoring (The "Gas" Model)
To prevent catastrophic data loss or malicious ledger deletion (e.g., if a server is wiped), enterprises need irrefutable proof of state. Tempus offers a premium API service that periodically anchors the latest ledger hash to public blockchains (Ethereum, Base, Solana). We charge a micro-transaction fee for every public timestamp, acting as a decentralized notary.

### 3. Enterprise Compliance Dashboard (SIEM Integration)
Auditors and Compliance Officers need human-readable interfaces, not JSON files in a terminal. The Enterprise License includes a rich web dashboard that connects to `tempus.db`, sets up real-time alerts for high-stakes financial decisions, generates PDF audit reports, and integrates seamlessly with corporate security tools like Splunk or Datadog.

### 4. Dispute Resolution as a Service
As B2A (Business-to-Agent) transactions scale, agents will inevitably dispute outcomes (e.g., "My agent paid, but yours didn't deliver the code"). By standardizing on Tempus DDB, we can offer automated, cryptographic arbitration services that read both agents' ledgers, verify signatures, and issue neutral, legally-binding verdicts for an arbitration fee.

### 5. Agentic Payment Gateway ("Stripe for AI")
Tempus DDB is already the layer where agents use cryptographic keys (Ed25519) to sign critical decisions. A premium module will bridge these signatures directly to smart contracts (USDC) or fiat banking APIs. This allows Tempus to process the actual financial movement triggered by the decision and capture a percentage fee per transaction.

## WASM Status

WASM support is experimental and currently uses in-memory stub storage. Do not rely on it for persistent ledgers or audit workflows yet.

## Releasing

1. Update version in `pyproject.toml` and `Cargo.toml`
2. Update `CHANGELOG.md`
3. Commit and tag: `git tag vX.Y.Z`
4. Push tag: `git push origin vX.Y.Z`
5. Create GitHub Release (the release.yml will build and attach wheels automatically)
6. (Optional) Publish to PyPI: use the release workflow or `maturin publish`

---

## Contributing

We welcome contributions that keep the core simple and focused.

1. Fork the repo
2. Make changes on a feature branch
3. Ensure tests pass (`python -m pytest` or the existing integration tests)
4. Open a PR

---

**Tempus DDB** — Give your agents a memory they can't rewrite.
