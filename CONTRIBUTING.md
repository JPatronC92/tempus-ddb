# Contributing to Tempus DDB

Thank you for your interest in contributing to Tempus DDB!

## Code of Conduct

We are committed to providing a friendly, safe and welcoming environment for all.

## How to Contribute

1. Fork the repository.
2. Create a feature branch (`git checkout -b feat/amazing-feature`).
3. Make your changes.
4. Ensure tests pass (`pytest tests/` and `cargo test`).
5. Commit your changes (`git commit -m 'Add some amazing feature'`).
6. Push to the branch.
7. Open a Pull Request.

## Development Setup

```bash
git clone https://github.com/JPatronC92/tempus-ddb.git
cd tempus-ddb
python -m venv .venv
python -m pip install -e .[dev]
```

Python 3.10 or newer and a stable Rust toolchain are required.

## Testing

Run the same core checks enforced by CI:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
ruff check .
pytest -p no:cacheprovider
```

Tests and examples must use temporary workspaces. Do not commit databases, keys,
credentials, logs, caches, wheels, or build output.

## Pull Request Guidelines

- Keep PRs focused.
- Update documentation if needed.
- Add tests for new functionality.
- Preserve fail-closed behavior for unknown schema, policy, and execution states.
- Update `CHANGELOG.md` for user-visible changes.

## Security Changes

Do not open a public issue for a suspected vulnerability. Follow
[SECURITY.md](SECURITY.md). Security-sensitive pull requests should document the trust
boundary they change and include an adversarial regression test.

## Questions?

Open an issue or discussion.

Thank you!
