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
  it's a tier-0 service in prod.
- **REQUIRE_HUMAN** if it's production, or the budget is low (< 25% left).
- **ALLOW** only when it's reversible, non-prod, and the budget is healthy.

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

## Roadmap

- MCP server mode, so AI agents (Claude Code, kagent, etc.) can call the gate as a tool.
- Budget adapters for Prometheus / SigNoz (compute `remaining_budget` from live SLIs).
- A `dry_run` blast-radius estimator (stubbed today).

## License

MIT.
