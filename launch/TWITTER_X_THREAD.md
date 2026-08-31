# 🐦 X (Twitter) Launch Thread

## Tweet 1 (Hook + Video / GIF)
Most AI agent frameworks are one prompt injection away from wiping production data or draining API balances.

Giving raw database credentials to an LLM is a fatal design flaw.

Today we're launching **Tempus DDB (v0.4.0)** — an open-source, fail-closed B2A cryptographic security gate for autonomous AI actions. 🧵👇

[Attach 15-20s demo video or GIF of Trace Demo]

---

## Tweet 2 (The Problem)
Why do traditional "guardrails" fail?

Because system prompts and text filters are voluntary. A clever jailbreak or hallucination bypasses them entirely.

If the agent process holds the API key, the blast radius is unlimited.

---

## Tweet 3 (The Solution: B2A Toll)
Tempus enforces a 4-step cryptographic toll:

1️⃣ **Intent:** Agent cryptographically signs what it wants to do (no credentials).
2️⃣ **Policy:** Tempus Gate issues an expiring, single-use signed permit.
3️⃣ **Execution:** Mediated executor checks the permit and runs with isolated keys.
4️⃣ **Receipt:** Tamper-evident, auditable execution receipt.

---

## Tweet 4 (Architecture)
Built from the ground up for extreme performance and local-first reliability:

🦀 High-speed Rust core + Python bindings (`pip install tempus-ddb`)
⚡ SQLite in WAL mode
🔑 Ed25519 signatures + Vault Transit support
🔌 Model Context Protocol (MCP) native server

---

## Tweet 5 (Interactive Demo)
You don't even need to install it to test tamper detection.

We built an interactive, browser-based trace verifier:

👉 https://elbuilder77.github.io/tempus-ddb/trace.html

Modify any payload field in memory and watch the cryptographic signatures immediately fail.

---

## Tweet 6 (CTA / Links)
Tempus DDB is 100% open source under MIT:

⭐ GitHub: https://github.com/elbuilder77/tempus-ddb
📦 PyPI: https://pypi.org/project/tempus-ddb/
📖 Docs: https://elbuilder77.github.io/tempus-ddb/docs.html

Let us know what you think! Repost & star if you care about AI agent security. 🛡️
