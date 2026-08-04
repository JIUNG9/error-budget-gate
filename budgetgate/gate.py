"""The core gate. Pure function: decide allow / require-human / block.

The rule: automation may PROPOSE a fix; the error budget decides whether it ACTS.
"""

from .actions import is_reversible
from .models import Action, GateDecision, Service, Tier

LOW_BUDGET_THRESHOLD = 0.25  # below this, escalate to a human even in non-prod


def evaluate(
    action: Action, service: Service, budget_remaining: float, env: str = "dev"
) -> GateDecision:
    """Return a GateDecision for an automated action. No side effects."""
    env = (env or "dev").lower()
    # Trust the allow-list over a caller-supplied flag.
    reversible = bool(action.reversible) and is_reversible(action.name)

    # --- hard BLOCKs ---
    if not reversible:
        return GateDecision(False, False, f"BLOCK: '{action.name}' is not a reversible action")
    if budget_remaining <= 0:
        return GateDecision(
            False, True, "BLOCK: error budget exhausted — page a human, no automated action"
        )
    if service.tier == Tier.TIER_0 and env == "prod":
        return GateDecision(
            False, True, "BLOCK(human): tier-0 service in prod — requires human approval"
        )

    # --- REQUIRE_HUMAN ---
    if env == "prod":
        return GateDecision(
            False, True, "REQUIRE_HUMAN: production action — propose and wait for approval"
        )
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
