# Tempus Domain Context

Tempus is a cryptographic toll gate for autonomous agent actions, enforcing zero-trust authorization, single-use permits, strict credential isolation, and tamper-evident receipts.

## Language

### Actors & Boundaries

**Gate**:
The authorization authority and delegation root that evaluates deterministic tenant policy and issues signed, single-use permits.
_Avoid_: Proxy, Firewall, Gateway

**Requesting Agent**:
An autonomous entity or LLM requesting an external effect, authenticated strictly by its registered Ed25519 public key.
_Avoid_: Bot, Client, Caller, User

**Mediated Executor**:
A credential-isolated execution process that holds downstream secrets, validates and atomically consumes a permit, and executes external effects.
_Avoid_: Worker, Runner, Tool adapter, Sidecar

**Tenant**:
An isolated administrative and cryptographic domain possessing its own delegation root, policies, agent registry, and action history.
_Avoid_: Workspace, Account, Organization

### Protocol Primitives & Contracts

**Intent**:
A canonical payload signed by a requesting agent declaring the exact requested action, resource, arguments, and idempotency key.
_Avoid_: Request, Command, Prompt, Invocation

**Permit**:
An expiring, single-use authorization receipt signed by the Gate binding the action, policy digest, and actor identity with an `ALLOWED` or `BLOCKED` decision.
_Avoid_: Token, Grant, Ticket, Session, Scope

**Outcome**:
A canonical payload signed by a mediated executor recording the external result (`SUCCEEDED`, `FAILED`, or `UNKNOWN`) and downstream references.
_Avoid_: Response, Return value, Output object

**Execution Receipt**:
A dual-signed cryptographic record binding the intent digest, authorization permit, executor observation, and final gate linkage.
_Avoid_: Log entry, Audit record, Event row

**Trace**:
The complete four-phase cryptographic chain (Intent ➔ Authorization ➔ Outcome ➔ Receipt) that can be verified mathematically offline.
_Avoid_: Audit trail, History log, Telemetry trace

**Checkpoint**:
A signed, monotonic external state attestation that makes ledger truncation, alteration, or database rollback detectable.
_Avoid_: Database snapshot, Backup marker, State dump

### Category & Architecture

**Decision Database**:
The technical category descriptor for Tempus as an append-only, tamper-evident cryptographic decision ledger.
_Avoid_: General-purpose database, SQL store, Application database
