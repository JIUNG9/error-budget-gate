# error-budget-gate

**An error-budget gate for automated remediation.** Before any automated action
runs — a remediation, a deploy, an AI agent's "fix" — `budgetgate` answers one
question: *can we afford for this to act right now, unattended?*

[![ci](https://github.com/JIUNG9/error-budget-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/JIUNG9/error-budget-gate/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![deps](https://img.shields.io/badge/runtime%20deps-0-1a8917)](pyproject.toml)

> Automation may **propose** the fix. The error budget decides whether it **acts**.

`budgetgate` is a tiny, pure, dependency-free function. You give it the action, the
service, how much error budget is left, and the environment. It returns
**allow / require-human / block**, with a one-line reason.

> ⚠️ **Status: alpha (0.1.0a1).** The design is proven by real incidents, not by
> years in production. APIs may change. Use it to think, then to gate dev, then prod.

## Why this exists

A real one: an autoscaler replaced a single unhealthy instance **6 times in 22
minutes** — a 23-minute outage with no page and no logs, because the automation
could *act* but had no *gate*. "Self-healing" with no judgment about cost isn't
healing; it's churn.

Most "AI agent guardrails" gate on a **human approval** or a **static policy**
(OPA/Cedar). `budgetgate` gates on the thing SRE already measures and those tools
skip: the **error budget**. It composes with them — it's the SLO-aware policy they
can call.

## The gate logic

- **BLOCK** if the action isn't reversible, or the error budget is exhausted, or
  it's a tier-0 service in prod (or an unrecognised env).
- **REQUIRE_HUMAN** if it's production or an environment it doesn't recognise (only
  `dev`, `development`, `test`, `qa`, `staging`, `sandbox` and `local` count as
  non-prod by default; see below), the budget is low (< 25% left), or the budget
  isn't a finite number (NaN or infinity) or is above 1: unknown is never treated as healthy.
- **ALLOW** only when it's reversible, non-prod, and the budget is healthy.

To opt in your own environment names, pass `non_prod_envs` to `evaluate` (or
`--non-prod-env NAME`, repeatable, on the command line). The list replaces the default set,
names are matched case-insensitively, and `prod` or `production` raises `ValueError`:

```python
evaluate(action, service, 0.8, env="preprod", non_prod_envs=["preprod", "dev"])
```

`remaining_budget` and `burn_rate` raise `ValueError` on impossible input (negative
counts, `good_events > total_events`, an SLO target outside 0 to 1) rather than
returning a clamped number.

The reversible-action allow-list is explicit; anything destructive
(`delete`/`destroy`/`terminate`/…) is never reversible, no matter what flag you pass.

## Quickstart

```python
from budgetgate import Action, Service, Tier, evaluate, remaining_budget

budget = remaining_budget(good_events=995, total_events=1000, slo_target=0.99)  # 0.5

decision = evaluate(
    action=Action("rollout_restart", reversible=True, est_duration_s=30),
    service=Service("checkout", tier=Tier.TIER_2),
    budget_remaining=budget,
    env="dev",
)
print(decision.allow, decision.requires_human, decision.reason)
# True False  ALLOW: reversible 'rollout_restart', 50% budget left, env=dev
```

The repository is `error-budget-gate`; the import package is `budgetgate`, the same
way `python-dateutil` imports as `dateutil`.

```bash
git clone https://github.com/JIUNG9/error-budget-gate && cd error-budget-gate
pip install -e ".[dev]"
python -m pytest -q
```

## Command line

```bash
python -m budgetgate --action rollout_restart --service checkout --budget 0.8 --env dev
# ALLOW: reversible 'rollout_restart', 80% budget left, env=dev
echo $?   # 0
```

| Exit code | Decision |
| --- | --- |
| 0 | allow |
| 10 | require human |
| 20 | block |
| 2 | bad arguments |

`--non-prod-env NAME` (repeatable) replaces the built-in set of non-prod environments.
`--tier` (0 to 3, default 2) sets the service tier and `--json` prints the decision as JSON.
The action's reversibility comes from the allow-list, not from a flag. `--budget nan` requires a
human, the same as passing NaN to `evaluate`.

## Budget from Prometheus

If your SLI is a Prometheus ratio, the adapter reads it and returns the remaining budget.
The query must return one sample between 0 and 1:

```python
from budgetgate import remaining_budget_from_prometheus

budget = remaining_budget_from_prometheus(
    "http://prometheus.monitoring.svc:9090",
    'sum(rate(http_requests_total{job="checkout",code!~"5.."}[30d]))'
    ' / sum(rate(http_requests_total{job="checkout"}[30d]))',
    slo_target=0.99,
)
```

It uses the standard library only (`urllib`), accepts `http://` and `https://` URLs, and takes
`timeout=` and `headers=` (for example an `Authorization` header). If the query returns no
data, several series, NaN (no traffic in the window) or an error, it raises `PrometheusError`.
It does not guess a budget. Catch the error and decide, or pass `float("nan")` to `evaluate`,
which requires a human.

## Roadmap

- MCP server mode, so AI agents (Claude Code, kagent, etc.) can call the gate as a tool.
- A budget adapter for SigNoz (Prometheus is done).
- A `dry_run` blast-radius estimator (stubbed today).

## License

MIT.
