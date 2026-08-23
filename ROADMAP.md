# Tempus DDB roadmap

Tempus DDB is currently a beta. The local authorization protocol, signed policy and
identity lifecycle, Vault Transit signer, and credential-isolated GitHub executor are
implemented and covered by automated tests. The project is not yet a horizontally
durable or independently checkpointed service.

The roadmap is ordered by security dependency: durability comes before a hosted audit
experience, and one production-grade executor path comes before a broad adapter catalog.

## Available in the 0.4 line

- Versioned intent, authorization, outcome, receipt, trace, and verification contracts.
- Separate gate, requesting-agent, and executor Ed25519 identities.
- Signed deterministic policies with reproducible evidence and closed reason codes.
- Tenant-scoped delegation, rotation, revocation, and historical key resolution.
- Single-use expiring permits and fail-closed executor recovery.
- Local and Vault Transit signing through the same provider boundary.
- A GitHub executor for exactly bound issue and pull-request creation.
- Autonomous MCP tools, adapter conformance fixtures, SBOM generation, and release
  attestations.
- Bounded SQLite connection pooling for executor state transitions.

## 0.5 — Durable local operations

- Stream validation and export so large ledgers do not require a second in-memory copy.
- Define an append-only receipt event contract independent of SQLite.
- Add signed external checkpoints that make database rollback or deletion detectable.
- Publish backup, restore, reconciliation, and disaster-recovery procedures.
- Add multi-process contention and recovery tests for permit consumption.

Exit criteria: a restored deployment preserves idempotency and consumption state, and a
reviewer can detect rollback against an independently stored checkpoint.

## 0.6 — Service deployment

- Introduce a transport-neutral gate service around the existing signed contracts.
- Add tenant isolation, quotas, rate limits, and explicit retention controls.
- Provide opt-in OpenTelemetry metrics for decision latency, execution latency, replays,
  expirations, policy denials, and `UNKNOWN` outcomes.
- Package a least-privilege GitHub App deployment path.
- Validate one distributed event-store implementation against the local conformance suite.

Exit criteria: multiple gate instances can process independent actions without weakening
single-consumption or historical verification guarantees.

## 1.0 — General availability

- Complete an independent security review and remediate high-severity findings.
- Exercise release, upgrade, key rotation, revocation, backup, and incident procedures in
  a clean environment.
- Publish signed reproducible artifacts with provenance and an SPDX SBOM.
- Provide a read-only audit API and console that never becomes part of the authorization
  path.
- Document the supported deployment profiles and their availability guarantees.

## Product principles

- No permit, no effect; every effect produces a verifiable receipt.
- Humans inspect history but do not sit in the autonomous transaction loop.
- Unknown schemas, policies, identities, and execution states fail closed.
- Credentials belong to mediated executors, never to requesting agents.
- Performance, availability, and compliance statements require reproducible evidence.

Security assumptions and current limitations are maintained in
[THREAT_MODEL.md](THREAT_MODEL.md). Compatibility commitments are maintained in
[COMPATIBILITY.md](COMPATIBILITY.md).
