# Changelog

## [Unreleased]

### Added

- First complete local B2A authorization flow: signed action intent, gate permit,
  executor outcome, final receipt, trace reading, and end-to-end verification.
- Stable versioned JSON contracts and closed machine statuses for autonomous consumers.
- Signed, immutable agent registration events with a gate delegation root.
- Deterministic action idempotency, expiring permits, and single-consumption outcomes.
- Rust, Python, CLI, and MCP B2A surfaces plus replay/tamper/authorization tests.
- Source-of-truth B2A implementation plan and production-oriented threat model.
- Signed MCP authorization and outcome tools for clients that keep agent and executor
  private keys outside the gate process.
- Signed executor observations for `STARTED`, `SUCCEEDED`, `FAILED`, and `UNKNOWN`, plus
  restart recovery that never replays an ambiguous external effect.
- Packaged `tempus-github-executor` for exactly bound GitHub issue and pull-request
  creation with an executor-only credential.
- A public product roadmap with ordered Phase 3 trust and adoption milestones.
- Dependabot coverage for Cargo, Python, and GitHub Actions dependencies.

### Changed

- MCP defaults to the autonomous execution-gate surface. Administrative, legacy, and
  destructive tools now require explicit environment flags.
- Product positioning now treats money as optional action metadata and humans as
  read-only auditors rather than transaction approvers.
- Default MCP mode now exposes only signed B2A write tools. The compatibility tools
  that receive local keyfile paths require `TEMPUS_LOCAL_KEYFILE_TOOLS=1`.
- Phase 2 is complete for the single-instance GitHub adapter, including policy-version
  checks, exact argument binding, credential isolation, and crash recovery.
- Package metadata now reflects the actual Python 3.10+ MCP dependency and alpha status.
- The Python package exports its installed version and the GitHub executor derives its
  user-agent version from package metadata.
- Tests and runnable examples use self-cleaning temporary workspaces instead of leaving
  databases and generated keys in the repository root.

### Security

- Agent registrations can no longer be silently replaced.
- The gate signing key is server-controlled for MCP authorization requests.
- Unregistered agents are blocked before execution and conflicting permit reuse is
  rejected.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-06-26

### Changed
- Updated examples to the current free core API.
- Added smoke-test coverage for runnable example scripts.
- Stabilized release readiness for the free/open-core packaging and CI path.

## [0.2.0] - 2026-06-26

### Added
- Comprehensive CLI improvements: `tempus record`, `tempus status`, `tempus --version`
- Expanded test coverage with Python API tests and CLI integration tests
- Multiple end-to-end examples in `examples/`
- GitHub Actions CI workflow for multi-OS/Python testing
- Module docstrings and improved Python API documentation

### Changed
- Removed license gate entirely from Rust core and Python bindings for true free/open nature
- Simplified `TempusDDB` constructor to `TempusDDB(db_path, keyfile)`
- Updated positioning to emphasize "free, local-first, tamper-evident"
- Improved error handling and UX across CLI

### Fixed
- License generation to properly support direct CLI usage
- Constructor calls in tests and examples

## [0.1.0] - Previous

Initial public version with core Rust engine, MCP integration, and basic CLI.
