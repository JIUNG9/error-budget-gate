"""Report how the gate would classify an action, with no side effects.

This is a preview of the reversibility check `evaluate` applies, not a blast-radius
estimate: it does not look at the service's dependencies, replicas or traffic.
"""

from .actions import is_reversible
from .models import Action, DryRunResult, Service


def dry_run(action: Action, service: Service) -> DryRunResult:
    """Return the reversibility verdict for `action` and the duration the caller declared.

    `reversible` uses the same rule as `evaluate`: the caller's flag AND the allow-list.
    `est_duration_s` is echoed from the action, not measured.
    """
    reversible = bool(action.reversible) and is_reversible(action.name)
    return DryRunResult(
        action=action.name,
        service=service.name,
        reversible=reversible,
        rollback_available=reversible,
        est_duration_s=action.est_duration_s,
        note=(
            "reversible — safe to attempt behind the gate"
            if reversible
            else "NOT reversible — the gate will block automated execution"
        ),
    )
