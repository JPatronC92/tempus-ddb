<div align="center">
  <img src="assets/logo.png" alt="Tempus DDB" width="180" />

# Tempus DDB

**The B2A security gate for autonomous agent actions**

Local-first · Fail-closed contracts · Ed25519 receipts · MCP-native
</div>

Tempus sits between an agent's intent and an external effect. The agent signs what it
wants to do, Tempus issues a short-lived permit, an executor performs the effect, and
the executor plus Tempus sign the outcome. A human is not part of the transaction loop;
humans only inspect the resulting history.

> **Product invariant:** no Tempus permit, no effect; every effect produces a verifiable
> receipt.

The current `main` branch implements the first complete local vertical slice of that
contract. It does **not** yet include the credential-holding executor proxy, remote KMS,
external checkpoints, or a web audit console. See [B2A_IMPLEMENTATION_PLAN.md](B2A_IMPLEMENTATION_PLAN.md)
and [THREAT_MODEL.md](THREAT_MODEL.md) for the exact boundary.

## What is implemented

- Stable machine contracts with explicit `schema_version` values.
- Separate Ed25519 identities for the Tempus gate, requesting agent, and executor.
- Immutable, gate-signed agent registration receipts. Registrations cannot be silently
  overwritten.
- `ALLOWED` or `BLOCKED` authorization before execution.
- Short-lived permits, deterministic action IDs, and idempotency conflict detection.
- Single-consumption execution receipts; an identical retry is idempotent and a
  conflicting second outcome is rejected.
- End-to-end verification of intent, gate authorization, executor outcome, and receipt
  linkage.
- Money is optional metadata in the same universal action envelope; financial and
  non-financial actions use the same protocol.
- An autonomous MCP surface that hides administrative, legacy, and destructive tools by
  default.

## B2A flow

```text
agent signs intent
        │
        ▼
Tempus request_action ── BLOCKED ──► signed denial trace
        │ ALLOWED
        ▼
single-use, expiring permit
        │
        ▼
executor performs effect and signs outcome
        │
        ▼
Tempus commit_outcome ──► final signed execution receipt
        │
        ▼
human or machine calls verify_trace
```

Tempus becomes an unavoidable toll only when the executor or downstream API holds the
real credentials and refuses requests without a valid Tempus permit. The current repo
provides the permit protocol; mediated executor adapters are the next production phase.

## Install

```bash
pip install tempus-ddb
```

Development checkout:

```bash
python -m pip install -e .
```

## Bootstrap identities

`tempus init` creates the local gate key and database, then records the gate as the
signed delegation root. This is deployment-time bootstrap, not a human approval step
for each action.

```bash
tempus init
tempus keygen --output agent.keys.json
tempus keygen --output executor.keys.json

tempus register-agent --alias purchasing-agent --agent-keyfile agent.keys.json
tempus register-agent --alias purchasing-executor --agent-keyfile executor.keys.json
```

The gate key is the global `--keyfile` for the Python CLI and defaults to `keys.json`.
Production deployments should replace plaintext key files with a KMS/HSM-backed signer.

## Python quickstart

```python
import json
import time
from tempus_ddb import TempusDDB, gen_keys

gen_keys("gate.keys.json")
gen_keys("agent.keys.json")
gen_keys("executor.keys.json")

gate = TempusDDB("tempus.db", "gate.keys.json")

with open("gate.keys.json", encoding="utf-8") as handle:
    gate_id = json.load(handle)["public_key"]
with open("agent.keys.json", encoding="utf-8") as handle:
    agent_id = json.load(handle)["public_key"]
with open("executor.keys.json", encoding="utf-8") as handle:
    executor_id = json.load(handle)["public_key"]

gate.register_agent(gate_id, "tempus-gate", '{"can_delegate":true}')
gate.register_agent(agent_id, "purchasing-agent", "{}")
gate.register_agent(executor_id, "purchasing-executor", "{}")

intent = json.dumps({
    "schema_version": "tempus.action-intent.v1",
    "tenant_id": "acme",
    "agent_id": agent_id,
    "idempotency_key": "purchase-2026-07-16-001",
    "action_type": "purchase",
    "resource": "vendor-api/compute-credits",
    "requested_at": time.time_ns() // 1_000,
    "input": {"sku": "compute-credits"},
    "money": {"amount": "25.00", "asset": "USD", "beneficiary": "vendor-42"},
})

authorization = json.loads(gate.request_action(intent, "agent.keys.json", 60))
permit = authorization["authorization"]
assert permit["decision"] == "ALLOWED"

# The executor performs the external effect only after checking the permit.
outcome = json.dumps({
    "schema_version": "tempus.action-outcome.v1",
    "authorization_id": permit["authorization_id"],
    "action_id": permit["action_id"],
    "status": "SUCCEEDED",
    "external_reference": "vendor-tx-9182",
    "output": {"credits_added": 1000},
})

receipt = gate.commit_outcome(
    permit["authorization_id"],
    outcome,
    "executor.keys.json",
)
verification = json.loads(gate.verify_trace(permit["action_id"]))
assert verification["status"] == "VERIFIED"
assert verification["phase"] == "COMPLETED"
```

For remote transports, use `request_action_signed(...)` so the agent signs locally and
never sends its private key or keyfile to Tempus.

## Stable contracts

| Contract | Schema |
|---|---|
| Agent intent | `tempus.action-intent.v1` |
| Authorization response | `tempus.authorization-result.v1` |
| Signed permit | `tempus.authorization-receipt.v1` |
| Executor outcome | `tempus.action-outcome.v1` |
| Execution response | `tempus.execution-result.v1` |
| Signed execution receipt | `tempus.execution-receipt.v1` |
| Complete trace | `tempus.action-trace.v1` |
| Verification result | `tempus.trace-verification.v1` |

Authorization decisions are `ALLOWED` or `BLOCKED`. Execution outcomes are `SUCCEEDED`
or `FAILED`. Trace verification is `VERIFIED` or `INVALID`.

## MCP autonomous mode

The default MCP surface exposes only machine-to-machine execution and read-only audit
operations:

| Tool | Purpose |
|---|---|
| `tempus_request_action` | Obtain a signed, expiring permit |
| `tempus_commit_outcome` | Consume a permit with an executor-signed result |
| `tempus_get_trace` | Read authorization and execution evidence |
| `tempus_verify_trace` | Verify the complete action trace |
| `tempus_list_agents` | Read signed agent identities |

Configuration:

```json
{
  "mcpServers": {
    "tempus": {
      "command": "tempus",
      "args": ["mcp", "start"],
      "env": {
        "TEMPUS_MODE": "autonomous",
        "TEMPUS_GATE_KEYFILE": "keys.json"
      }
    }
  }
}
```

Provisioning should run separately from the agent-facing MCP process. The following
flags are deliberately off by default:

| Flag | Unlocks |
|---|---|
| `TEMPUS_ADMIN_TOOLS=1` | init, key generation, signed agent registration, whoami |
| `TEMPUS_LEGACY_TOOLS=1` | old voluntary `record`, list, export, count, validate tools |
| `TEMPUS_DESTRUCTIVE_TOOLS=1` | demo-only cleanup |

## Human audit

Humans are readers, not approvers:

```bash
tempus trace --action-id <action-id>
tempus verify-trace --action-id <action-id>
tempus list-agents
```

The future audit console will be read-only and derive its views from these contracts.

## Legacy ledger

The original `record`, `validate`, `list`, `count`, and `export` interfaces remain for
compatibility and migration. They are a voluntary flight recorder and do not enforce
the B2A toll. New autonomous integrations should use the action authorization flow.

## Security boundary

This implementation detects receipt and trace alteration, rejects unregistered actors,
prevents conflicting idempotent requests, and prevents two outcomes from consuming one
permit. It does not yet prevent deletion of the entire local database or bypass by an
agent that still possesses downstream credentials. Read [THREAT_MODEL.md](THREAT_MODEL.md)
before using Tempus for high-impact production actions.

## Development

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
ruff check .
pytest -p no:cacheprovider
python -m maturin build
```

## License

MIT. See [LICENSE](LICENSE).
