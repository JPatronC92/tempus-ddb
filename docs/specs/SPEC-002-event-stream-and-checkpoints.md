# SPEC-002: Append-Only Event Stream & Monotonic External Checkpoints

**Status:** ready-for-agent  
**Domain Context:** [CONTEXT.md](../../CONTEXT.md)  
**Target Milestone:** 0.5 (Durable Local Operations & External Checkpoints)

---

## Problem Statement

Currently, Tempus DDB persists registrations, authorizations, and execution receipts in local SQLite tables (`agents`, `action_authorizations`, `action_outcomes`). While individual records are cryptographically signed with Ed25519:
1. SQLite storage is mutable on disk. A compromised host or malicious operator can delete records (tail truncation) or restore an older snapshot (rollback attack) without being detected locally.
2. Exporting and validating large ledgers requires loading full JSON copies into memory, creating performance bottlenecks for long-running deployments.
3. There is no storage-agnostic append-only event stream contract, tying event verification directly to SQLite table structures.

---

## Solution

1. Define an append-only canonical event contract (`tempus.event-stream.v1`) where every state transition (agent registration, policy update, authorization permit, execution outcome) forms a cryptographically linked SHA-256 hash chain (`prev_event_hash` ➔ `event_digest`).
2. Implement signed monotonic external checkpoints (`tempus.checkpoint.v1`) issued by the Gate that bind `checkpoint_sequence`, `stream_root_hash`, event counts, and timestamps.
3. Provide an incremental stream validation and checkpoint verification engine (`tempus.checkpoint-verification.v1`) that detects database deletion, truncation, alteration, or rollback against an independently stored external checkpoint.

---

## User Stories

1. As a Security Officer, I want Tempus to emit signed monotonic checkpoints, so that I can detect if a database backup was rolled back to an older state.
2. As a Compliance Auditor, I want to verify an exported event stream against an external checkpoint offline, so that I have mathematical proof of ledger completeness without accessing the live database.
3. As a Platform Operator, I want to stream events incrementally without loading the entire database into memory, so that memory usage remains constant regardless of ledger size.
4. As a Disaster Recovery Engineer, I want clear reconciliation procedures when restoring from backup, so that I can verify the restored database matches the latest external checkpoint before resuming agent operations.
5. As a System Architect, I want the event stream schema to be storage-agnostic, so that Milestone 0.6 can validate alternative distributed event backends against the same conformance suite.
6. As an Agent Developer, I want checkpoint creation to be non-blocking, so that normal authorization permit issuance latency (< 5ms) is never impacted.

---

## Implementation Decisions

### Wire Schemas & Contracts
- **`tempus.event-stream-event.v1`**:
  - `sequence_number`: 64-bit strictly monotonic integer (1, 2, 3...).
  - `tenant_id`: string.
  - `event_id`: deterministic unique identifier.
  - `event_type`: enum (`agent.registered`, `policy.published`, `action.authorized`, `action.executed`, `action.unknown`).
  - `payload_hash`: SHA-256 digest of canonical payload JSON.
  - `prev_event_hash`: SHA-256 digest of preceding event (or `0000...` for genesis).
  - `timestamp`: UTC microseconds.
  - `event_digest`: SHA-256 digest of canonical event metadata.

- **`tempus.checkpoint.v1`**:
  - `checkpoint_id`: string (UUID or deterministic hash).
  - `tenant_id`: string.
  - `checkpoint_sequence`: strictly increasing monotonic counter.
  - `first_sequence`: starting event sequence in checkpoint window.
  - `last_sequence`: ending event sequence in checkpoint window.
  - `stream_root_hash`: cumulative SHA-256 digest representing stream state at `last_sequence`.
  - `total_events`: total count of events covered.
  - `created_at`: UTC microseconds.
  - `gate_id`: Gate Ed25519 public key.
  - `signature`: Ed25519 signature over canonical checkpoint envelope.

- **`tempus.checkpoint-verification.v1`**:
  - `status`: `VERIFIED` or `INVALID`.
  - `checkpoint_id`: string.
  - `events_verified`: integer.
  - `reason_code`: `CHECKPOINT_VALID`, `ERR_SIGNATURE_INVALID`, `ERR_STREAM_HASH_MISMATCH`, `ERR_SEQUENCE_GAP`, `ERR_ROLLBACK_DETECTED`.

### Storage & Engine Architecture
- SQLite table `event_stream` added to Gate database:
  - Indexed by `(tenant_id, sequence_number)` and `(tenant_id, event_id)`.
- Core methods added in Rust (`src/phase3.rs` / `src/lib.rs` / PyO3 bindings):
  - `create_checkpoint(tenant_id: &str) -> Result<String, String>`
  - `export_event_stream(tenant_id: &str, from_seq: u64, limit: u32) -> Result<String, String>`
  - `verify_checkpoint_stream(checkpoint_json: &str, stream_json: &str) -> Result<String, String>`
- CLI subcommands added to `tempus`:
  - `tempus checkpoint create --tenant-id <id> --out <checkpoint.json>`
  - `tempus checkpoint export --tenant-id <id> --from-seq 1 --out <stream.jsonl>`
  - `tempus checkpoint verify --checkpoint <checkpoint.json> --stream <stream.jsonl>`

---

## Testing Decisions

### What Makes a Good Test
- Tests must verify cryptographic invariants and state detection:
  1. Contiguous stream generation ➔ Checkpoint produces `VERIFIED`.
  2. Modifying a single byte in any past event ➔ `ERR_STREAM_HASH_MISMATCH`.
  3. Deleting tail events (truncation) ➔ `ERR_STREAM_HASH_MISMATCH` / `ERR_SEQUENCE_GAP`.
  4. Presenting an older checkpoint against a newer stream (rollback simulation) ➔ `ERR_ROLLBACK_DETECTED`.
  5. Multi-tenant isolation: Tenant A's checkpoint never validates Tenant B's stream.

### Modules Tested & Prior Art
- `tests/test_checkpoints.py`
- Integration with CLI tests in `tests/test_cli.py`.

---

## Out of Scope

- Remote cloud blob storage uploaders (S3/GCS Object Lock connectors - scheduled for 0.6 / Enterprise).
- Distributed multi-gate Raft consensus (scheduled for 0.6).
- Public blockchain anchoring (explicitly out of scope).

---

## Further Notes

- Checkpoint generation is deterministic and reproducible from any clean replay of the event stream.
