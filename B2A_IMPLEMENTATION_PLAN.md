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

The repo includes a generic mediated executor and a packaged GitHub REST adapter. The
adapter holds its token outside the agent process, binds the signed action type,
repository, and arguments to the outbound request, and records signed executor states.
This completes the single-instance Phase 2 boundary for the supported GitHub actions.
It is not yet an enterprise boundary: deployments still need to ensure the agent cannot
obtain the GitHub token, and KMS, distributed consumption, and rich policy are later
phases.

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

Status: implemented for the single-instance GitHub adapter.

Completed:

- Generic `TempusExecutor` and SQLite-backed single-consumption store.
- Gate identity, tenant, authorization integrity, intent-hash, expiry, and replay checks
  before an adapter produces an effect.
- Explicit policy-version validation inside the executor.
- Packaged `tempus-github-executor` adapter for GitHub issue and pull-request creation;
  the token is read by the executor process and is never accepted in the permit.
- Exact binding of `action_type`, `resource`, and the complete allowlisted argument set
  to the GitHub REST request.
- Atomic consume-before-effect semantics with signed `STARTED`, `SUCCEEDED`, `FAILED`,
  and `UNKNOWN` executor observations.
- Restart recovery converts abandoned `STARTED` operations to `UNKNOWN` and never
  retries an ambiguous external effect.
- End-to-end tests for bypass, replay, expiry, tampering, cross-tenant use, argument
  rejection, definitive failure, ambiguous transport failure, and crash recovery.

Exit gate:

- Satisfied for `github.create_issue` and `github.create_pull_request` in a
  single-instance executor deployment.
- A requesting agent without the executor-held credential cannot produce the supported
  external effect.
- Replayed, expired, altered, cross-tenant, or already-consumed permits are rejected by
  the executor itself.
- Executor crash recovery produces a signed `UNKNOWN` observation and cannot create an
  untraceable duplicate effect.

### Phase 3 — Policy, delegation, and workload identity

Status: planned.

Implementation order:

1. Introduce a signer and verification-key resolver interface. Preserve Ed25519 for v1
   receipts and attach a stable signer URI plus key version to new identities.
2. Replace the hard-coded `baseline-v1` policy marker with signed, versioned,
   deterministic policy bundles controlled by the gate. Include decision reason codes,
   policy digest, and evidence digest in every permit.
3. Add tenant-scoped delegation, signed revocation, and key-rotation events. Verification
   resolves the key that was valid at signing time, so historical receipts survive
   rotation and later revocation.
4. Add workload identity for gate and executor services, then implement the first remote
   signer with an end-to-end conformance suite.
5. Add algorithm agility through a new contract version before integrating providers
   that cannot produce Ed25519 signatures. A cloud KMS name alone is not assumed to be
   compatible with the existing v1 receipt format.
6. Exercise the same policy engine against money and non-money actions using the
   universal action envelope.

Exit gate:

- No production key requires a plaintext private-key file.
- Historical receipts remain verifiable after rotation or revocation.
- Unknown policy versions fail closed.
- Policy and signer-provider conformance fixtures pass without network credentials.

Product and adoption milestones are tracked in [ROADMAP.md](ROADMAP.md).

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
