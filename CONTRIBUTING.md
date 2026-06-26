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
pip install -e .
```

For Rust changes:

```bash
cargo build
```

## Testing

- Python tests: `pytest tests/ -v`
- Rust tests: `cargo test`
- CLI tests are included in the Python test suite.

## Pull Request Guidelines

- Keep PRs focused.
- Update documentation if needed.
- Add tests for new functionality.

## Questions?

Open an issue or discussion.

Thank you!