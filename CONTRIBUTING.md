# Contributing

Bug reports and PRs are welcome. The bar for this project is narrow on purpose.

## The design constraint

The gate is a **pure function with zero runtime dependencies**. It takes numbers and
strings, returns a decision, and touches nothing else. No network calls, no clients,
no config file loading, no logging side effects.

That constraint is the point. It means you can unit-test your remediation policy
without standing up Prometheus, and it means the gate can't be the thing that breaks
during an incident. PRs that add a dependency to the core package will be asked to
move that code into an adapter instead.

Adapters (Prometheus, SigNoz, Cloud Monitoring) belong in an optional extra with
their own dependency group, and they should do one job: produce the `good_events` /
`total_events` / `slo_target` numbers the pure functions already accept.

## Running it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

Lint before you push:

```bash
pip install ruff
ruff check . && ruff format --check .
```

## What a good PR looks like

- One behavior change per PR.
- A test that fails before your change and passes after.
- If you change a gate decision, say which real failure mode motivated it. The gate
  table is small and every branch needs to justify itself — "it seemed safer" isn't
  enough, because a gate that blocks too much gets disabled, and a disabled gate
  protects nothing.
- New gate branches go in `gate.py` in the existing block → require-human → allow
  order, so the function still reads top-to-bottom as "most restrictive first."

## Reporting an incident-shaped bug

If the gate allowed something it shouldn't have, the most useful report is the four
inputs: action name, service tier, budget remaining, environment. That's enough to
reproduce it as a one-line test.
