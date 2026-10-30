# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [PEP 440](https://peps.python.org/pep-0440/).

## [Unreleased]

### Documentation

- `dry_run` is documented as a reversibility preview that uses the same rule as `evaluate`. It
  was described as a blast-radius estimator "stubbed today"; it never estimated blast radius,
  and the README and docstring now say so.

### Changed

- Renamed the distribution and repository to `error-budget-gate` so the name says
  what it does. The import package stays `budgetgate` — short at the call site,
  the same way `python-dateutil` imports as `dateutil`.

### Fixed

- `evaluate` no longer returns ALLOW when `budget_remaining` is NaN. NaN fails every
  comparison, so it skipped all guards. A non-finite budget now requires a human.

- `evaluate` no longer treats an unrecognised `env` ("production", "prd", an empty
  string) as non-prod. Only an explicit non-prod set (`dev`, `development`, `test`,
  `qa`, `staging`, `sandbox`, `local`) can ALLOW; anything else is handled like prod.
  `env=None` or `""` used to default to `dev`.

- `remaining_budget` and `burn_rate` raise `ValueError` for negative counts and for
  `good_events > total_events`, and both check `slo_target` (even with zero traffic).
  These used to be clamped into a plausible-looking number.
- `evaluate` requires a human when `budget_remaining` is above 1, instead of allowing.

### Added

- `evaluate(..., non_prod_envs=...)` and `--non-prod-env` let a site name its own non-prod
  environments (for example `preprod`). The default set is unchanged, and `prod` or
  `production` in the list raises `ValueError`.

- `python -m budgetgate` (also installed as `budgetgate`): evaluates one action from flags,
  prints the decision and exits 0 (allow), 10 (require human) or 20 (block).
- Prometheus budget adapter. `remaining_budget_from_prometheus(base_url, query, slo_target)` runs
  an instant query that returns the SLI as a ratio and converts it to remaining budget.
  `remaining_budget_from_sli` does the same math for a ratio you already have. Standard
  library only. No data, several series, NaN or an HTTP error raise `PrometheusError`
  instead of producing a budget.
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
