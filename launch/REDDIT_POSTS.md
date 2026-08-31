# 🔴 Reddit Distribution Kit

---

## 1. r/LocalLLaMA & r/AI_Agents
**Title:** `I built an open-source, local-first cryptographic gate for AI agent actions (Rust + Python + SQLite)`

**Body:**
Hey everyone!

When building autonomous agents (with LangChain, CrewAI, AutoGen, or local Ollama/vLLM setups), the standard approach of giving raw API tokens and DB connections directly to the agent runtime makes me nervous. One prompt injection or rogue reasoning step and you have unmitigated writes.

I built **Tempus DDB** (v0.4.0) to solve this with a local-first **B2A (Bot-to-Agent)** security gate:

* **Intent Signing:** The agent only signs its intention with Ed25519; it never sees downstream secrets.
* **Deterministic Policy:** The gate evaluates tenant rules and issues an expiring, single-use signed permit (`ALLOWED` or `BLOCKED`).
* **Mediated Executor:** An isolated executor holds the downstream credentials and only fires when holding a valid permit.
* **Tamper-Evident Receipts:** Every outcome generates an immutable cryptographic receipt.
* **MCP Native:** Works out-of-the-box as an MCP server with Claude Desktop / Cursor.

It's written in Rust with Python bindings, stores everything locally in SQLite WAL mode, and is available on PyPI (`pip install tempus-ddb`).

* **Interactive Browser Demo:** https://elbuilder77.github.io/tempus-ddb/trace.html
* **GitHub Repo:** https://github.com/elbuilder77/tempus-ddb

Would love feedback from the community!

---

## 2. r/Python
**Title:** `Tempus DDB: A Rust-powered Python library for zero-trust authorization in AI agent workflows`

**Body:**
Hey Pythonistas,

We just released **Tempus DDB v0.4.0** on PyPI (`pip install tempus-ddb`). It's a Python/Rust library designed to solve authorization and execution auditing for autonomous agent tools.

Instead of letting agents execute tools directly:
1. The agent signs an action intent payload.
2. Tempus evaluates policy and issues a single-use permit.
3. The executor verifies the permit and executes the function with isolated credentials.
4. An immutable cryptographic trace is recorded and verifiable.

Check out the cookbook for LangChain/LangGraph:
https://github.com/elbuilder77/tempus-ddb/blob/main/cookbooks/langchain_agent_guard.py

Feedback on API design and threat model is very welcome!

---

## 3. r/Rust
**Title:** `Tempus DDB: A local-first B2A security gate and tamper-evident ledger built with PyO3, Ed25519-dalek, and Rusqlite`

**Body:**
Hi Rustaceans,

Wanted to share a project we've been building: **Tempus DDB** (https://github.com/elbuilder77/tempus-ddb).

It's a high-performance, fail-closed security gate for AI agent workflows. We chose Rust for the cryptographic core (Ed25519-dalek, SHA-256 state hashing) and SQLite WAL concurrency (via r2d2 and rusqlite), and exposed clean Python bindings using PyO3 and Maturin.

Key crates & design highlights:
* Max LTO compilation (`codegen-units = 1`, `lto = true`)
* Deterministic canonical JSON serialization
* Fast in-memory key caching
* Platform wheels for Linux (manylinux), macOS (x86_64 + ARM64), and Windows.

Check it out on GitHub and let us know your thoughts on the Rust architecture!
