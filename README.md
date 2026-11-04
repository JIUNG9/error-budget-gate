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
  the 1-hour burn rate is 14.4 or more, or it's a tier-0 service in prod (or an
  unrecognised env).
- **REQUIRE_HUMAN** if it's production and the prod policy below isn't met, or an environment it doesn't recognise (only
  `dev`, `development`, `test`, `qa`, `staging`, `sandbox` and `local` count as
  non-prod by default; see below), the budget is low (< 25% left), or the budget
  isn't a finite number (NaN or infinity) or is above 1: unknown is never treated as healthy.
  A 6-hour burn rate of 6 or more, or a NaN burn rate, also requires a human.
- **ALLOW** when it's reversible, non-prod, and the budget is healthy, or when the prod policy
  below is met.

### Production policy

In `env == "prod"` the gate allows an unattended action only when all of these hold:

- the action is on the reversible allow-list,
- the service is tier 1, 2 or 3 (tier 0 always needs a human),
- `budget_remaining` is at least 50%,
- `burn_rate_1h` is passed and is below 1.0 (the budget is not being spent faster than the SLO
  window allows), and the 1h and 6h blocks above don't apply.

Anything else in prod is REQUIRE_HUMAN, including a missing `burn_rate_1h`: without it the gate
can't tell whether the budget is draining now. The 50% floor and the 1.0 burn ceiling are
`PROD_MIN_BUDGET` and `PROD_MAX_BURN_1H` in `budgetgate/gate.py`. Names such as `production` or
`prd` are not `prod`; they are unknown and never take this path.

```python
evaluate(action, Service("checkout", Tier.TIER_2), 0.8, env="prod", burn_rate_1h=0.4)  # ALLOW
```

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

### Burn rate

The remaining budget says how much is left. The burn rate says how fast it is going.
Pass `burn_rate_1h` and `burn_rate_6h` (see `burn_rate`) to `evaluate`, or
`--burn-rate-1h` and `--burn-rate-6h` on the command line:

| Input | Threshold | Decision |
|-------|-----------|----------|
| `burn_rate_1h` | 14.4 or more | BLOCK (exit 20) |
| `burn_rate_6h` | 6 or more | REQUIRE_HUMAN (exit 10) |
| either, NaN | | REQUIRE_HUMAN |
| either, negative | | `ValueError` (CLI exit 2) |

The thresholds are the fast and slow page levels from the Google SRE Workbook chapter
"Alerting on SLOs" (14.4x over 1 hour spends 2% of a 30-day budget; 6x over 6 hours spends 5%).
Both inputs are optional. Without them the decision depends only on the remaining budget,
as before. Each window is compared on its own. The Workbook also pairs each window with a
shorter one (5 minutes, 30 minutes) so an alert clears quickly; that confirmation window is
not modelled here, so a burn that has already stopped can still hold the gate until the
longer window recovers.

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

## Dry run

`dry_run(action, service)` previews how the gate classifies an action without evaluating
a budget or environment. It returns a `DryRunResult` with `reversible` (the same rule as
`evaluate`: the caller's flag and the allow-list must both say yes), `rollback_available`
(equal to `reversible`), `est_duration_s` (copied from the action, not measured) and a `note`.

```python
dry_run(Action("rollout_restart", reversible=True, est_duration_s=30), Service("checkout"))
# DryRunResult(action='rollout_restart', service='checkout', reversible=True, ...)
```

It is not a blast-radius estimate. It does not read the service's replicas, dependencies or
traffic, so a reversible action can still be unsafe to run; the gate's budget and tier
checks cover that.

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

### JSON output

With `--json` the command prints one JSON object on a single line. The exit code is the same
as without the flag.

```bash
python -m budgetgate --action rollout_restart --service checkout --budget 0.1 --env prod --json
# {"allow": false, "requires_human": true, "reason": "REQUIRE_HUMAN: ...", "exit_code": 10}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `allow` | boolean | `true` only for an allow decision (exit code 0) |
| `requires_human` | boolean | `true` when a person must act: on every exit 10, and on blocks for an exhausted budget or a tier-0 service in prod |
| `reason` | string | The same one-line text printed without `--json`; it starts with `ALLOW`, `REQUIRE_HUMAN` or `BLOCK` (`BLOCK(human)` for tier-0 in prod) |
| `exit_code` | integer | 0, 10 or 20, equal to the process exit code |

`allow: false` with exit 20 is a block. `requires_human` can be `true` or `false` on a block,
so branch on `exit_code`, not on `requires_human`. Bad arguments exit 2 and print the
error to stderr, not JSON. Non-ASCII characters in `reason` are escaped (`\u2014`), so parse
the output with a JSON parser rather than matching on the raw text.

### Use in CI

Any step that runs the command can branch on its exit code. This GitHub Actions step lets an
allow through, stops the job for a human on exit 10, and fails the job on exit 20:

```yaml
- name: Error budget gate
  id: gate
  run: |
    set +e
    python -m budgetgate --action rollout_restart --service checkout \
      --budget "$BUDGET_REMAINING" --env "$TARGET_ENV" --json | tee gate.json
    code=${PIPESTATUS[0]}
    echo "code=$code" >> "$GITHUB_OUTPUT"
    exit 0

- name: Deploy
  if: steps.gate.outputs.code == '0'
  run: ./deploy.sh

- name: Wait for approval
  if: steps.gate.outputs.code == '10'
  run: echo "A person must approve this change." && exit 1

- name: Blocked
  if: steps.gate.outputs.code == '20'
  run: jq -r .reason gate.json && exit 1
```

`BUDGET_REMAINING` and `TARGET_ENV` come from your own earlier steps, for example the
Prometheus adapter above. `PIPESTATUS` keeps the gate's exit code instead of `tee`'s. If the
code is 2 or anything else, none of the three later steps runs, so add a final step that fails
the job on any other value if you need that case covered.

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
- A blast-radius estimate for `dry_run` (replicas, dependants, traffic share); it only reports reversibility today.

## License

MIT.
