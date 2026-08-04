# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

### Changed

- Renamed the distribution and repository to `error-budget-gate` so the name says
  what it does. The import package stays `budgetgate` — short at the call site,
  the same way `python-dateutil` imports as `dateutil`.

### Added

- CI: pytest on Python 3.10–3.13, plus `ruff check` and `ruff format --check`.
- `CONTRIBUTING.md` and this changelog.

## [0.1.0a1] — 2026-06-13

First alpha. The gate is a pure function with no dependencies and no I/O.

### Added

- `evaluate()` — the gate. Returns allow / require-human / block with a reason string.
- `remaining_budget()` and `burn_rate()` — error-budget arithmetic over good/total event
  counts, clamped to `[0, 1]`.
- `is_reversible()` — explicit reversible-action allow-list. Destructive verbs
  (`delete`, `destroy`, `drop`, `terminate`, `wipe`, `purge`) can never be reversible,
  regardless of the flag a caller passes.
- `dry_run()` — reports what an action would do, with no side effects.
- Frozen dataclasses for `Action`, `Service`, `Tier`, `GateDecision`, `DryRunResult`.
- 19 unit tests covering the budget math, the allow-list, and every gate branch.

[Unreleased]: https://github.com/JIUNG9/error-budget-gate/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/JIUNG9/error-budget-gate/releases/tag/v0.1.0a1
