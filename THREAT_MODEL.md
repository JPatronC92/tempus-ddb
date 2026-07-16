# Tempus DDB B2A Threat Model

## Scope and invariant

Tempus is a security gate for autonomous business-to-agent and agent-to-agent actions.
Its target invariant is:

> No valid Tempus permit, no external effect; every external effect produces a
> cryptographically verifiable receipt.

The current release implements the local authorization and receipt protocol. The
invariant becomes operationally enforceable only when the downstream executor holds the
real credentials and rejects every request that lacks a valid, unexpired, unused Tempus
permit.

Humans are outside the per-action approval loop. They may provision the deployment trust
root and inspect history, but agents, the gate, and executors perform the runtime flow.

## Protected assets

- Agent action intents and their input digests.
- Gate authorization and denial receipts.
- Executor outcomes and external references.
- Linkage between intent, authorization, and outcome.
- Gate, agent, and executor signing keys.
- Signed agent registration and delegation records.
- Tenant action history and verification results.
- Downstream credentials held by mediated executors.

## Trust boundaries

1. **Requesting agent:** untrusted until its signature and signed registration verify.
2. **Tempus gate:** trusted to evaluate the configured policy and sign permits. Its key
   must be provisioned as the delegation root.
3. **Executor:** trusted to hold downstream credentials and report the external outcome;
   its identity and output are signed and independently verifiable.
4. **SQLite storage:** untrusted mutable storage. Signatures detect alteration, but local
   storage alone cannot prove that a complete database was not deleted or rolled back.
5. **MCP transport:** agent-controlled input. The autonomous surface exposes no direct
   record, registration, key-generation, or cleanup tools by default.
6. **Human auditor:** read-only consumer of traces. Human approval is not a security
   dependency for an action to proceed.

## Implemented controls

### Signed identity delegation

- The first agent registration must be the gate key itself.
- The gate registration becomes the signed root and receives delegation authority.
- Every subsequent registration is signed by an active delegator.
- Registrations are insert-only; an alias or metadata record cannot be replaced silently.
- Legacy unsigned `agents` rows are not trusted for B2A authorization.

### Agent intent proof

- Every action uses `tempus.action-intent.v1`.
- `agent_id` must match the Ed25519 key that signs the canonical intent.
- Unknown or untrusted agents receive a signed `BLOCKED` authorization.
- Invalid schema, mismatched identity, and malformed JSON fail closed.

### Permit integrity and replay protection

- The gate signs an authorization receipt containing the action, actor, intent hash,
  policy version, decision, issue time, and expiry.
- `action_id` is deterministic for tenant, agent, and idempotency key.
- Repeating the same request returns the original authorization.
- Reusing an idempotency key for a different intent is rejected.
- Permit TTL is bounded to 1–86,400 seconds.

### Outcome integrity and single consumption

- Only an active registered executor can commit an outcome.
- The executor signs the canonical `tempus.action-outcome.v1` payload.
- The gate signs the final execution receipt and links it to the authorization and intent
  hash.
- An identical retry returns the existing receipt.
- A conflicting second outcome is rejected as an already-consumed permit.

### MCP least privilege

The default MCP process exposes only authorization, outcome commit, trace verification,
trace reading, and registry reading. Separate environment flags are required for:

- `TEMPUS_ADMIN_TOOLS=1`: deployment-time provisioning.
- `TEMPUS_LEGACY_TOOLS=1`: voluntary pre-B2A ledger methods.
- `TEMPUS_DESTRUCTIVE_TOOLS=1`: demo cleanup.

The gate key path is server-controlled through `TEMPUS_GATE_KEYFILE`; an MCP client
cannot select a different gate key per authorization request.

## Threats and residual risk

| Threat | Current control | Residual risk / required production control |
|---|---|---|
| Agent bypasses Tempus | Signed permit protocol | Still possible if the agent possesses downstream credentials. Move credentials into a mediated executor that requires the permit. |
| Agent forges identity | Ed25519 intent signature and signed registration | A stolen agent private key can impersonate that agent. Add KMS workload identity, rotation, and revocation. |
| Client self-registers | Registration requires a delegation-capable gate key; admin MCP tools are disabled | Protect the separate provisioning process and gate key. Add explicit tenant-scoped delegation policies. |
| Gate forges permits | Gate receipts identify and are signed by the gate | The gate is a trust root. Use KMS/HSM, key transparency, replicated audit, and external checkpoints. |
| Replay or duplicate action | Deterministic action ID, idempotency uniqueness, permit expiry | A downstream adapter must also persist and enforce action/permit IDs. |
| Two conflicting outcomes | Unique authorization consumption | Distributed executors require transactional shared state or a consensus-backed permit store. |
| Receipt modification | Canonical hashes and Ed25519 signatures | Metadata confidentiality is not provided; values are stored as plaintext JSON. |
| Tail deletion or full database loss | None in local-only mode | Replicate append-only events and publish signed/Merkle checkpoints outside the host. |
| Database rollback | Signatures preserve integrity of the restored snapshot | A valid older snapshot is not distinguishable locally. External monotonic checkpoints are required. |
| Malicious policy supplied by agent | Current policy is fixed as `tempus.identity-gate.v1` | A future policy store must be gate-controlled, versioned, signed, and included in receipts. |
| Key file theft | File permissions only | Plaintext keyfiles are development mode. Production must use KMS/HSM or workload identity. |
| MCP path misuse | Paths are constrained to the configured sandbox | Current local MCP convenience flow accepts agent/executor keyfile paths. Remote transports must use signed payloads and never receive private keys. |
| Sensitive payload disclosure | None | Store digests or encrypted evidence where raw inputs/outputs contain secrets or personal data. |
| Financial abuse | Money uses the same signed envelope | Tempus does not provide custody, KYC/AML, sanctions controls, or transaction reversal. Financial executors must supply those controls. |

## Security statuses

- Authorization: `ALLOWED` or `BLOCKED`.
- Execution: `SUCCEEDED` or `FAILED`.
- Trace verification: `VERIFIED` or `INVALID`.
- Trace phase: `AUTHORIZED`, `COMPLETED`, `BLOCKED`, or `EXPIRED`.

A `FAILED` execution can still have a `VERIFIED` trace: verification means the evidence
is authentic and linked, not that the business operation succeeded.

## Production readiness gates

Tempus must not be described as an unavoidable production toll until all of the following
are true:

1. Downstream credentials are unavailable to requesting agents.
2. Executors verify the full permit, policy version, expiry, and consumption state before
   producing an effect.
3. Gate, agent, and executor keys use workload identity or KMS/HSM-backed signing.
4. Agent revocation and key rotation are signed, tenant-scoped, and tested.
5. Action receipts are replicated and externally checkpointed to detect truncation and
   rollback.
6. Policies are signed, versioned, deterministic, and controlled by the gate rather than
   by the requesting agent.
7. Concurrency, recovery, denial-of-service, and cross-process replay tests pass.
8. The agent-facing process cannot enable admin, legacy, or destructive MCP tools.
9. Confidentiality and retention controls match the data carried in action evidence.

## Out of scope for the current vertical slice

- Custody or movement of funds.
- Bilateral negotiation and arbitration.
- Human approval workflows.
- Cloud synchronization and external anchoring.
- A read-only web audit console.
- General domain policy evaluation beyond identity, signature, TTL, and replay checks.

These are roadmap items, not current security claims.
