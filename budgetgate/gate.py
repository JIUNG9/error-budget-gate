"""The core gate. Pure function: decide allow / require-human / block.

The rule: automation may PROPOSE a fix; the error budget decides whether it ACTS.
"""

import math
from collections.abc import Iterable

from .actions import is_reversible
from .models import Action, GateDecision, Service, Tier

LOW_BUDGET_THRESHOLD = 0.25  # below this, escalate to a human even in non-prod

# Environments that may act unattended. Anything else, including a typo such as
# "production" or "prd", is treated like prod: unknown is never assumed safe.
NON_PROD_ENVS = frozenset({"dev", "development", "test", "qa", "staging", "sandbox", "local"})

# A caller may widen the set with its own names, but never with these.
_PROD_ENVS = frozenset({"prod", "production"})


def _normalise_envs(envs: Iterable[str]) -> frozenset[str]:
    if isinstance(envs, str):
        raise TypeError("non_prod_envs must be a collection of names, not a single string")
    names = frozenset(str(e).strip().lower() for e in envs)
    if "" in names:
        raise ValueError("non_prod_envs must not contain an empty name")
    if names & _PROD_ENVS:
        raise ValueError(
            f"non_prod_envs must not contain a production name: {sorted(names & _PROD_ENVS)}"
        )
    return names


def evaluate(
    action: Action,
    service: Service,
    budget_remaining: float,
    env: str = "dev",
    non_prod_envs: Iterable[str] | None = None,
) -> GateDecision:
    """Return a GateDecision for an automated action. No side effects.

    `non_prod_envs` replaces the default NON_PROD_ENVS, so a site with an environment
    called "preprod" can opt it in. Names are compared case-insensitively. The set
    cannot include "prod" or "production", and it cannot be empty-named.
    """
    env = (env or "").strip().lower()
    allowed = NON_PROD_ENVS if non_prod_envs is None else _normalise_envs(non_prod_envs)
    non_prod = env in allowed
    # Trust the allow-list over a caller-supplied flag.
    reversible = bool(action.reversible) and is_reversible(action.name)

    # --- hard BLOCKs ---
    if not reversible:
        return GateDecision(False, False, f"BLOCK: '{action.name}' is not a reversible action")
    if not math.isfinite(budget_remaining):
        # NaN fails every comparison below, so it would fall through to ALLOW.
        return GateDecision(
            False, True, "REQUIRE_HUMAN: error budget unknown (not a finite number) — escalate"
        )
    if budget_remaining > 1:
        # A fraction above 1 means a broken SLI source; do not act on it.
        return GateDecision(
            False, True, f"REQUIRE_HUMAN: error budget {budget_remaining} is above 1 — escalate"
        )
    if budget_remaining <= 0:
        return GateDecision(
            False, True, "BLOCK: error budget exhausted — page a human, no automated action"
        )
    if service.tier == Tier.TIER_0 and not non_prod:
        return GateDecision(
            False, True, "BLOCK(human): tier-0 service in prod — requires human approval"
        )

    # --- REQUIRE_HUMAN ---
    if not non_prod:
        if env == "prod":
            reason = "REQUIRE_HUMAN: production action — propose and wait for approval"
        else:
            reason = f"REQUIRE_HUMAN: unknown env {env!r} — treated as production"
        return GateDecision(False, True, reason)
    if budget_remaining < LOW_BUDGET_THRESHOLD:
        return GateDecision(
            False, True, f"REQUIRE_HUMAN: budget low ({budget_remaining:.0%} left) — escalate"
        )

    # --- ALLOW ---
    return GateDecision(
        True,
        False,
        f"ALLOW: reversible '{action.name}', {budget_remaining:.0%} budget left, env={env}",
    )
