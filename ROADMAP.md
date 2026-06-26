# Tempus DDB — Executable Roadmap to Production & Public Launch

**Goal**: Turn Tempus DDB into a polished, trustworthy, easy-to-adopt open product that people (and agents) actually use in production.

**Current status**: Post-cleanup (removed paywall + legacy debt). Good definition + improved docs + better CLI. Logo added.

We treat this roadmap as **executable** — every item is a concrete task with owner, command, or file reference.

---

## Phase 0 — Definition & Documentation Polish (Current Sprint — A + B + D)

**Status**: In progress (this session)

### Done / In Progress
- [x] Strong product definition + one-liner + tagline ("The Tamper-Proof Flight Recorder for AI Agents")
- [x] Full README rewrite (logo, examples, chain explanation, security, tools)
- [x] CLI improvements (`record` subcommand, `--version`, better UX)
- [x] Logo integrated (`assets/logo.png`)
- [ ] Add 2–3 high-quality usage examples (Python + MCP)
- [ ] Create this ROADMAP.md + link from README
- [ ] Minor: update version string, help texts, pyproject description

**Next actions in this phase**
1. User reviews definition + README.
2. Final polish pass on docs (add one good end-to-end example).
3. Commit + push to `main` (as requested).

---

## Phase 1 — Core Stability & Developer Experience (1–2 weeks)

- [ ] Expand test coverage
  - Add Python tests for record + validate + chain integrity (`tests/`)
  - Add CLI integration tests (using subprocess)
- [ ] Improve error messages and UX in both Rust core and Python layer
- [ ] Add `tempus status` CLI command (show last record, db size, key fingerprint)
- [ ] Document the Python API properly (docstrings + simple Sphinx or mkdocstrings)
- [ ] Create `examples/` folder with:
  - `basic_record.py`
  - `agent_mcp_example.md`
  - `verify_chain.py`
- [ ] Add basic benchmarks (see existing `benchmark.py`) and document performance characteristics

**Success criteria**: `tempus record` works smoothly from CLI, `pytest` passes with >80% coverage on core flows.

---

## Phase 2 — Packaging, Distribution & Releases (1–2 weeks)

- [ ] Prepare for PyPI
  - Clean `pyproject.toml` (add long_description from README, proper classifiers, license)
  - Ensure `python -m build` or maturin produces clean wheels
  - Test install in clean venv: `pip install tempus_ddb`
- [ ] Rust crate
  - Update `Cargo.toml` with proper description, license, repository
  - `cargo publish --dry-run`
- [ ] GitHub Releases
  - Create release workflow (`.github/workflows/release.yml`)
  - Auto-build wheels for Windows/macOS/Linux + attach to release
  - Use `gh release create`
- [ ] Versioning policy (Semantic Versioning) + changelog (`CHANGELOG.md`)

**Success criteria**: `pip install tempus-ddb` (or the final name) works and `tempus --version` shows the released version.

---

## Phase 3 — Production Readiness (2–3 weeks)

- [ ] Security & Key handling
  - Review license check (currently very permissive for local use)
  - Document threat model (who can sign, what happens if keys are lost)
  - Consider key rotation story
- [ ] Reliability
  - Proper transaction handling in SQLite (already mostly there via rusqlite)
  - Add WAL mode or good defaults for concurrent use
  - Handle disk-full / corruption gracefully
- [ ] Performance & Scale
  - Run stress tests with 10k+ records
  - Document limits (single file SQLite is fine for most agent use cases)
- [ ] Documentation site (optional but recommended)
  - Use `mkdocs` + material or `mdbook`
  - Host on GitHub Pages (`docs/` folder)
  - Include "Getting started for agents" + "For developers building agent frameworks"
- [ ] Add CONTRIBUTING.md + CODE_OF_CONDUCT.md (if desired)

**Success criteria**: Can be used confidently for real high-stakes agent decisions with clear docs.

---

## Phase 4 — Launch & Ecosystem (Ongoing)

- [ ] v1.0 release on GitHub + announcement
  - Write launch post (X/Twitter, LinkedIn, r/MachineLearning, Hacker News, IndieHackers)
  - Create short demo video (30–60s) showing agent using it via Claude
- [ ] Community & Examples
  - Official examples repo or folder with LangGraph / AutoGen / CrewAI integration
  - "Agents using Tempus" showcase (collect real use cases)
- [ ] Distribution channels
  - Homebrew / winget / apt formula (later)
  - VS Code / Cursor extension idea (record decisions automatically?)
- [ ] Optional paid / hosted layers (future monetization)
  - Cloud sync & backup (Phase 4 of original roadmap)
  - Multi-agent shared ledgers
  - On-chain notarization service

---

## Phase 5 — Long-term Vision (6+ months)

- Multi-agent consensus primitives
- Rich querying / analytics over decision history
- Formal verification of the causal model (stretch)
- First-class support in major agent frameworks

---

## How to Work This Roadmap

1. Pick the next unchecked item.
2. Create a branch from `main`: `git checkout -b feat/xxx`
3. Make the change + add a test or example when possible.
4. Update this file (mark `[x]` and add date or PR link).
5. Open PR → merge to `main`.

**Current priority (as of this session)**: Finish Phase 0 cleanly → commit & push → start Phase 1.

---

**Owner note**: This document lives in the repo so anyone can contribute to the roadmap itself.

Last updated: during the definition + docs sprint (user request A+B+D).