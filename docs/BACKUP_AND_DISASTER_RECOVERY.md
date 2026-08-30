# Tempus DDB Backup, Restore, and Disaster Recovery Guide

> **Target Release Line:** `v0.5.0` (Durable Local Operations)  
> **Status:** Operational Specification & Architecture Guide

This document defines standard operating procedures for backing up, restoring, reconciling, and auditing Tempus DDB deployments, with explicit focus on **detecting rollback or deletion** using external signed checkpoints and append-only receipt streams.

---

## 1. Threat Model Context & Invariants

In single-instance SQLite deployments:
- **SQLite is mutable storage:** An attacker with root/filesystem access could delete `tempus.db` or roll back the database file to an earlier timestamp.
- **The Core Invariant:**
  > No valid Tempus permit, no external effect; every external effect produces a verifiable receipt.
- **The v0.5 Durability Invariant:**
  > Any rollback or deletion of past execution receipts must be deterministically detectable by comparing local ledger state against independently stored, signed checkpoint receipts.

---

## 2. Stable Contracts for Durability

### A. Append-Only Receipt Event (`tempus.receipt-event.v1`)

```json
{
  "schema_version": "tempus.receipt-event.v1",
  "sequence_number": 1042,
  "tenant_id": "acme",
  "action_id": "8f3b...12a",
  "authorization_id": "4c2a...99b",
  "receipt_id": "7e1d...55c",
  "intent_hash": "a1b2...c3d",
  "outcome_hash": "e5f6...789",
  "gate_id": "ed25519-gate-public-key-hex",
  "executor_id": "ed25519-executor-public-key-hex",
  "prev_event_hash": "3d9a...110",
  "event_hash": "fa08...44e",
  "gate_signature": "signature-hex",
  "emitted_at": 1787040012000000
}
```

### B. Signed Checkpoint Bundle (`tempus.checkpoint-bundle.v1`)

```json
{
  "schema_version": "tempus.checkpoint-bundle.v1",
  "checkpoint_id": "chk-2026-08-30-001",
  "tenant_id": "acme",
  "gate_id": "ed25519-gate-public-key-hex",
  "last_sequence_number": 1042,
  "last_action_id": "8f3b...12a",
  "merkle_root_hash": "99ee...00f",
  "total_records_count": 1042,
  "created_at": 1787040060000000,
  "gate_signature": "signature-hex"
}
```

---

## 3. Operational Backup Procedure

### Step 1: Safe Hot Backup via SQLite Online Backup API

Never use raw `cp` while the database is actively receiving write transactions. Use SQLite's online backup or `.backup` command to produce a point-in-time snapshot with write-ahead logging (WAL) consistency:

```bash
sqlite3 tempus.db ".backup 'tempus.backup-$(date +%Y%m%d%H%M%S).db'"
```

Or programmatically in Python:
```python
import sqlite3
import time

def backup_database(source_db_path: str, target_db_path: str):
    with sqlite3.connect(source_db_path) as src, sqlite3.connect(target_db_path) as dst:
        src.backup(dst, pages=100, sleep=0.01)
```

### Step 2: Publish Independent External Checkpoint

Generate a signed checkpoint bundle and push it to an append-only, write-once-read-many (WORM) storage destination (e.g. S3 Object Lock, Cloud Storage Bucket Retention, or dedicated audit ledger):

```bash
tempus export --json > /tmp/ledger_export.json
# Sign and push checkpoint digest to remote cold storage
aws s3 cp /tmp/checkpoint-bundle.json s3://acme-tempus-audit-checkpoints/$(date +%Y%m%d)/
```

---

## 4. Restore & Reconciliation Procedure

When restoring a database following hardware failure or disaster recovery:

1. **Restore base snapshot:**
   ```bash
   cp /backups/tempus.backup-latest.db ./tempus.db
   ```

2. **Verify Cryptographic Integrity:**
   Ensure no records have been corrupted:
   ```bash
   tempus doctor --json
   tempus conformance --signer
   ```

3. **Reconcile Against Independent Checkpoints:**
   Compare the latest local sequence number and Merkle root against the external checkpoint stored in WORM storage.
   - If `local_merkle_root != checkpoint_merkle_root`: **Tampering / Divergence detected! Fail closed.**
   - If `local_sequence_number < checkpoint_sequence_number`: **Rollback detected! Invalidate and alert security operations.**

4. **Verify Active Actor Registrations & Unconsumed Permits:**
   ```bash
   tempus list-agents
   tempus list-policies
   ```

---

## 5. Multi-Process Contention & Recovery Guarantees

1. **Single-Use Permit Consumption:**
   - The executor database and gate use SQLite WAL mode with `busy_timeout = 5000` ms.
   - All state transitions (`STARTED` -> `SUCCEEDED` / `FAILED` / `UNKNOWN`) execute inside immediate transactions.
2. **Ambiguous Crash Recovery:**
   - If an executor crashes while executing an external call, its observation remains in `STARTED` or `UNKNOWN`.
   - On restart recovery, Tempus marks the state `UNKNOWN` and **never automatically retries** an external effect.
