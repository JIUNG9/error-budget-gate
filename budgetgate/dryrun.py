"""Compute what an action WOULD do, with no side effects."""

from .actions import is_reversible
from .models import Action, DryRunResult, Service


def dry_run(action: Action, service: Service) -> DryRunResult:
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
