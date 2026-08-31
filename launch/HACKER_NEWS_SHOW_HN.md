# 📰 Hacker News (Show HN) Submission Kit

## Title Ideas (Pick One):
- **Option 1 (Recommended):** `Show HN: Tempus DDB – A fail-closed cryptographic gate for AI agent actions`
- **Option 2:** `Show HN: Tempus DDB – Don't give LLMs your database keys`
- **Option 3:** `Show HN: Tempus DDB – Zero-trust B2A security gate with verifiable receipts`

---

## URL:
`https://github.com/elbuilder77/tempus-ddb`

---

## Post Body / Text:

Hi HN,

We built **Tempus DDB** (https://github.com/elbuilder77/tempus-ddb) to solve a fundamental security flaw in autonomous AI agent systems: **giving raw downstream credentials directly to LLM agents and relying on prompt guardrails to keep them safe.**

Prompt guardrails (system prompts, regex filters, classifier models) are inherently advisory and prone to prompt injection. If an agent is compromised or hallucinates, it can wipe databases, drain balances, or perform unauthorized writes.

### How Tempus Solves This (The B2A Toll):
Tempus introduces an architectural, fail-closed **Bot-to-Agent (B2A)** security gate:

1. **Signed Intent:** The requesting agent signs its exact action payload using its own Ed25519 key. It has zero access to downstream API tokens or database credentials.
2. **Deterministic Policy & Permit:** Tempus Gate evaluates tenant-scoped policies and issues an expiring, single-use signed permit (`ALLOWED` or `BLOCKED`).
3. **Mediated Executor:** A separate executor holds the real API secrets and verifies the permit's cryptographic binding, tenant ID, and expiry before performing any effect.
4. **Tamper-Evident Receipts:** Both the gate and executor sign the outcome, generating a mathematically verifiable audit trail.

### Architecture & Tech Stack:
- **Core Engine:** High-performance Rust compiled with PyO3/Maturin (`pip install tempus-ddb`).
- **Ledger:** Local-first SQLite in WAL mode with fast serialization and in-memory key caching.
- **Signatures:** Ed25519 native + HashiCorp Vault Transit backend support.
- **Protocol:** MCP (Model Context Protocol) native server (`tempus mcp start`).

### Try it without installing:
We built a synthetic, browser-based trace verifier in WebAssembly/JS so you can test hash binding and tamper detection live:
👉 https://elbuilder77.github.io/tempus-ddb/trace.html

We would love feedback from the HN community on the threat model (https://github.com/elbuilder77/tempus-ddb/blob/main/THREAT_MODEL.md) and protocol contracts!
