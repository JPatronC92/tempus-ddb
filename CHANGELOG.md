# Changelog

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