# Tempus DDB public roadmap

Tempus DDB is a public-alpha candidate at `0.3.0`. Phase 2 is complete for a
single-instance GitHub executor that creates issues and pull requests. The next logical
step is not broad adapter growth or horizontal scale: it is making policy, identity
lifecycle, and production signing explicit enough that teams can trust the gate.

This roadmap separates protocol maturity from adoption. A milestone is complete only
when its exit criteria are tested and documented in the source tree.

## Before changing repository visibility

- [x] Generated databases, keys, caches, wheels, and build output are untracked and
  ignored.
- [x] License, security policy, threat model, code of conduct, contribution guide, issue
  templates, CI, and dependency updates are present.
- [x] Current files and Git history have been checked for common private-key and token
  signatures.
- [x] The release wheel and both packaged console commands have been exercised on a
  clean install.
- [ ] Enable private vulnerability reporting, Dependabot alerts, secret scanning, and
  push protection in GitHub repository settings.
- [ ] Protect `main` and require the Rust and Python CI jobs before merge.
- [ ] Configure PyPI Trusted Publishing and verify the `0.3.0` release from a clean
  environment after publication.
- [ ] Obtain an independent security-focused review of the Phase 2 boundary.

## Phase 3 — Policy and production identity

### 3.1 Signer and verifier boundary

- Define a Rust signer interface and verification-key resolver.
- Record signer URI, key version, and algorithm without exposing provider credentials.
- Preserve Ed25519 verification for every v1 receipt.
- Add offline provider-conformance fixtures.

Exit: the local file signer and a test remote signer pass the same contract suite, and
an unknown signer or algorithm fails closed.

### 3.2 Deterministic policy bundles

- Replace the hard-coded `baseline-v1` marker with signed, versioned policy bundles.
- Bind policy digest, evidence digest, and closed decision reason codes into permits.
- Cover resource, tenant, input, optional money metadata, TTL, and executor constraints.
- Reject unknown policy versions and non-deterministic inputs.

Exit: a reviewer can reproduce every allow/block decision from the signed evidence.

### 3.3 Identity lifecycle

- Add tenant-scoped delegation capabilities.
- Add signed agent and executor rotation and revocation events.
- Resolve the key valid at signing time so historical receipts remain verifiable.
- Define emergency revocation behavior for unconsumed permits.

Exit: rotation and revocation adversarial tests pass without invalidating historical
receipts.

### 3.4 Workload identity and first production signer

- Authenticate the gate and executor through workload identity instead of static service
  credentials.
- Select the first Vault/KMS/HSM integration by demonstrated algorithm and operational
  compatibility.
- Introduce a new contract version before using a provider that cannot sign Ed25519.
- Document availability, timeout, retry, and audit behavior for the provider.

Exit: no production private key is stored in a plaintext file, signer outages fail
closed, and integration tests run only through explicit opt-in credentials.

### 3.5 Operational readiness

- Add `tempus doctor` for configuration, permissions, clock, database, gate identity, and
  executor connectivity checks.
- Publish a machine-readable conformance suite for adapters.
- Produce an SBOM and signed release provenance.
- Define compatibility and deprecation policy for schemas, CLI, Python, and MCP tools.

Exit: a clean environment reaches a verified GitHub effect through documented commands
without editing source code.

## Adoption track

### Public alpha (`0.3.x`)

- Keep the repository secret-free, reproducible, and explicit about limitations.
- Reduce time to first verified GitHub effect to under 15 minutes.
- Publish one canonical GitHub quickstart and one failure/recovery guide.
- Recruit 3–5 design partners that already operate autonomous GitHub agents.
- Collect issues and opt-in feedback; do not add product telemetry by default.

### Design-partner beta (`0.4.x`)

- Deliver Phase 3.1–3.3 and the first production signer.
- Package a least-privilege GitHub App deployment path instead of relying only on a
  personal access token.
- Publish adapter conformance fixtures and a second adapter only after the GitHub path is
  repeatable.
- Provide migration notes and a documented support window for every contract change.

### General availability (`1.0`)

- Complete Phase 3 exit criteria and the Phase 4 durability subset required to detect
  database rollback or deletion independently.
- Complete an external security review and remediate high-severity findings.
- Ship signed, reproducible artifacts with an SBOM and verified release workflow.
- Publish operating guides for backup, recovery, rotation, revocation, and incident
  response.

## Adoption metrics

The primary activation metric is **time to first verified effect**: elapsed time from a
clean install to a `VERIFIED` completed GitHub trace. Supporting metrics are:

- successful clean-environment installs by supported OS and Python version;
- percentage of executed effects that end with a verified receipt;
- `UNKNOWN` outcomes and median reconciliation time;
- design partners reaching a second weekly verified effect;
- adapter conformance pass rate and upgrade success rate.

Metrics must be collected from explicit tests or opt-in operator reporting. Tempus does
not phone home by default.

## Explicit non-goals for Phase 3

- A write-capable human approval console.
- Many shallow adapters before one production-grade GitHub path.
- Multi-region ingestion before identity, policy, and key lifecycle are trustworthy.
- Compliance or performance claims without reproducible evidence.

Protocol details remain in [B2A_IMPLEMENTATION_PLAN.md](B2A_IMPLEMENTATION_PLAN.md),
scale architecture in [SCALING_PLAN.md](SCALING_PLAN.md), and security assumptions in
[THREAT_MODEL.md](THREAT_MODEL.md).
