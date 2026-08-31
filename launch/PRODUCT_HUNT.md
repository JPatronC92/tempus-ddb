# 🐱 Product Hunt Launch Kit

## 1. Product Details
* **Product Name:** Tempus DDB
* **Tagline:** The B2A cryptographic security gate for autonomous AI actions
* **Links:**
  * Website: https://elbuilder77.github.io/tempus-ddb/
  * GitHub: https://github.com/elbuilder77/tempus-ddb
  * PyPI: https://pypi.org/project/tempus-ddb/
* **Topics:** `Developer Tools`, `Artificial Intelligence`, `Open Source`, `Cybersecurity`, `Privacy`

---

## 2. Short Description (up to 255 chars)
A local-first, fail-closed security gate for AI agents. Prevents prompt-injection disaster with signed permits, credential isolation, and tamper-evident receipts.

---

## 3. Maker Comment (First Comment by Author)
Hey Product Hunt! 👋

We built **Tempus DDB** to address the elephant in the room for autonomous AI agents: **how do we let agents do real work (calling APIs, creating PRs, moving funds) without giving them unchecked access to raw credentials?**

Traditional guardrails are advisory prompt instructions. If an agent gets prompt-injected or hallucinates, those guardrails fail silently.

Tempus DDB enforces an architectural, zero-trust **B2A (Bot-to-Agent)** boundary:
1. 🛑 **Zero-Trust Toll:** Agents cryptographically sign what they want to do; they never see real API keys.
2. 🎟️ **Single-Use Signed Permits:** Tempus Gate evaluates deterministic policies and issues expiring permits.
3. 🔒 **Credential Isolation:** The mediated executor holds secrets and only acts with a valid permit.
4. 🧾 **Tamper-Evident Receipts:** Every outcome generates an immutable, verifiable cryptographic trace.

It's local-first, written in Rust with Python bindings, and available on PyPI: `pip install tempus-ddb`.

You can also test our in-browser trace verifier without installing anything: https://elbuilder77.github.io/tempus-ddb/trace.html

We’d love your feedback, questions, and ideas on how you secure your agent pipelines! 🛡️
