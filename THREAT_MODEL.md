# Threat Model

## Overview

Tempus DDB is a local-first, tamper-evident ledger for AI agent decisions. It provides cryptographic signing and hash chaining to detect unauthorized modifications.

## Assets

- Decision records (payloads, rules, signatures, hashes)
- Private signing keys (in keyfile)
- Database file (SQLite)

## Trust Boundaries

- Local machine filesystem
- The agent process using the library
- Human operators

## Threats

### 1. Unauthorized Modification of Records

- **Attacker**: Malicious actor with filesystem access.
- **Mitigation**: Ed25519 signatures + SHA-256 hash chain. Any change to payload, rules, or previous link will invalidate the signature or chain.
- **Detection**: `tempus verify` or `tempus_validate` will fail.

### 2. Key Compromise

- **Attacker**: Gains access to `keys.json`.
- **Impact**: Can forge new records.
- **Mitigation**: Keep keys file secure (file permissions, encryption at rest if needed). Rotate keys by starting new genesis chains.
- **Recommendation**: Store keys in secure locations (e.g., OS keyring in future versions).

### 3. Database Deletion or Loss

- **Impact**: Loss of history.
- **Mitigation**: Tempus DDB is tamper-evident, not deletion-proof. Users are responsible for backing up `tempus.db` and `keys.json`; the project does not provide replication (yet).

### 4. Supply Chain / Malicious Library

- **Mitigation**: Open source. Review code, use pinned dependencies.

### 5. MCP Tool Misuse

- Agents calling tools incorrectly.
- **Current mitigation**: Clear error messages and structured errors.
- **Future mitigation**: Idempotency keys or client-side request identifiers may be added later, but they are not implemented today.

## Out of Scope

- Cloud synchronization (future feature).
- Multi-agent consensus (future).
- Protection against physical theft of the entire machine.

## Recommendations for Users

- Use file permissions to protect `keys.json` and `tempus.db`.
- Regularly run `tempus verify`.
- Include decision context in payloads for auditability.
- For high-stakes, consider external anchoring of root hashes (future).