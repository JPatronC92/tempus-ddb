# Tempus DDB — B2A Source-of-Truth Plan

## Product direction

Tempus is infrastructure for autonomous business-to-agent and agent-to-agent execution.
It is not a human approval workflow and it is not only a voluntary flight recorder.

The product invariant is:

> No Tempus permit, no effect; every effect produces a verifiable receipt.

The primary customer is a business operating autonomous agents. The primary interface is
machine-to-machine. The only human product surface is read-only inspection of agent and
action history.

This document supersedes the earlier roadmap centered on shared ledgers, bilateral
agreements, escrow, and a supervisory dashboard. Money is optional action metadata, not
the organizing principle of the core protocol.

## Implemented baseline on `main`

### B2A contracts

- `tempus.action-intent.v1`
- `tempus.authorization-result.v1`
- `tempus.authorization-receipt.v1`
- `tempus.action-outcome.v1`
- `tempus.execution-result.v1`
- `tempus.execution-receipt.v1`
- `tempus.action-trace.v1`
- `tempus.trace-verification.v1`
- `tempus.agent-registration.v1`

### Runtime flow

1. A registered agent signs a canonical action intent.
2. Tempus validates identity, schema, idempotency, and the built-in identity policy.
3. Tempus persists and signs an `ALLOWED` or `BLOCKED` authorization.
4. An active executor consumes an allowed, unexpired permit exactly once.
5. The executor signs the outcome and Tempus signs the final execution receipt.
6. `verify_trace` validates both proofs and their linkage.

### Implemented safeguards

- Separate gate, agent, and executor keys.
- Signed, immutable registration receipts and a gate delegation root.
- Fail-closed handling for unknown agents and invalid contracts.
- Deterministic action IDs and idempotent retries.
- Conflict detection for reused idempotency keys.
- Expiring permits and single outcome consumption.
- Receipt tamper detection.
- MCP least privilege: admin, legacy, and destructive tools are disabled by default.

### Current limitation

The repo implements the permit protocol but not yet the credential-holding executor proxy.
An agent that still owns downstream credentials can bypass Tempus. Therefore the current
state is a validated vertical slice, not a production security boundary.

## Architecture target

```text
requesting workload
        │ signed action intent
        ▼
Tempus Gate API
  ├─ workload identity
  ├─ deterministic policy engine
  ├─ idempotency/replay store
  └─ signed permit issuer
        │ short-lived capability
        ▼
Mediated Executor
  ├─ owns downstream credentials
  ├─ verifies and consumes permit
  └─ signs observed outcome
        │
        ▼
Replicated Receipt Store + External Checkpoints
        │
        ▼
Read-only Audit API / Console
```

## Roadmap

### Phase 1 — Local B2A contract

Status: implemented and test-backed.

- Stable JSON contracts and status enums.
- Gate/agent/executor signatures.
- Signed registration root.
- Authorization, outcome, trace, and verification APIs.
- Python, Rust CLI, Python CLI, and MCP surfaces.
- Replay, conflict, tamper, and unauthorized-agent tests.

Exit gate:

- Rust format, Clippy, and all-target tests pass.
- Python Ruff and pytest pass.
- Wheel builds and imports from the built artifact.

### Phase 2 — Enforced executor mediation

Status: next.

- Define an executor adapter contract that accepts only a complete Tempus permit.
- Move downstream API keys, wallets, and service credentials out of the agent process.
- Verify permit signature, policy version, TTL, action digest, tenant, and consumption
  state inside the executor.
- Add atomic consume-before-effect semantics and crash recovery.
- Add signed `STARTED`, `SUCCEEDED`, `FAILED`, and `UNKNOWN` observations where required.
- Prove bypass prevention with an end-to-end adapter test.

Exit gate:

- A requesting agent cannot produce the external effect without a Tempus permit.
- Replayed, expired, altered, cross-tenant, or already-consumed permits are rejected by
  the executor itself.
- Executor crash recovery cannot create an untraceable duplicate effect.

### Phase 3 — Policy, delegation, and workload identity

Status: planned.

- Signed, versioned, deterministic policy bundles controlled by the gate.
- Tenant-scoped delegation capabilities.
- Signed agent/executor revocation and key rotation events.
- KMS/HSM and cloud workload identity signer interfaces.
- Decision reasons and evidence hashes included in every permit.
- Policy tests for money and non-money actions using the same envelope.

Exit gate:

- No production key requires a plaintext private-key file.
- Historical receipts remain verifiable after rotation or revocation.
- Unknown policy versions fail closed.

### Phase 4 — Durable distributed receipts

Status: planned.

- Append-only replicated event ingestion.
- Per-action concurrency without a single global linear-write bottleneck.
- Monotonic sequence or transparency-log checkpointing.
- External signed or Merkle checkpoints to detect rollback and tail deletion.
- Encrypted evidence storage and configurable retention.
- Tenant isolation, quotas, rate limiting, and disaster recovery.

Exit gate:

- Deletion or rollback of a local database is independently detectable.
- Recovery preserves idempotency and permit-consumption state.
- Cross-process concurrency and partition tests pass.

### Phase 5 — Read-only human audit product

Status: planned.

- Timeline filtered by tenant, agent, executor, action, risk, result, and money metadata.
- Evidence view: intent digest, policy version, reason codes, signatures, and external
  references.
- Clear distinction between business status and cryptographic verification status.
- Export and SIEM integration.
- No approve, reject, or execute controls in the audit interface.

Exit gate:

- An auditor can reconstruct an action from intent through external outcome without
  terminal access.
- The UI never becomes a runtime dependency for autonomous execution.

## Explicit non-goals

- Human approval for individual actions.
- Fund custody in the core ledger.
- A separate protocol for payments.
- Agent-supplied policies treated as authoritative.
- Mutable identity aliases used as proof of authority.
- A dashboard that can directly trigger actions.

## Production metrics

- Percentage of attempted effects that carry a verified Tempus permit.
- Percentage of completed effects with a verified execution receipt.
- Permit decision latency p50/p95/p99.
- Executor receipt latency and unknown-outcome rate.
- Replay, expiry, identity, policy, and cross-tenant rejection counts.
- Trace verification success rate.
- Time required for an auditor to reconstruct one action.

Commercial metering should count authorized/verified actions, retention, policy execution,
and audit exports. The protocol applies whether an action moves money or not.
