"""Pure error-budget math. No I/O — feed it event counts from your SLO source."""


def _validate(good_events: int, total_events: int, slo_target: float) -> None:
    """Reject inputs that cannot come from a real SLI instead of clamping them away."""
    if not 0.0 < slo_target < 1.0:
        raise ValueError("slo_target must be strictly between 0 and 1")
    if good_events < 0 or total_events < 0:
        raise ValueError("event counts must not be negative")
    if good_events > total_events:
        raise ValueError(f"good_events ({good_events}) cannot exceed total_events ({total_events})")


def remaining_budget(good_events: int, total_events: int, slo_target: float) -> float:
    """Fraction of the error budget still available, clamped to [0, 1].

    error budget (allowed bad) = (1 - slo_target) * total_events
    consumed (actual bad)      = total_events - good_events
    remaining fraction         = 1 - consumed / allowed

    Raises ValueError for an SLO target outside (0, 1), negative counts, or
    ``good_events > total_events``: a bad input is an error, not a full budget.
    """
    _validate(good_events, total_events, slo_target)
    if total_events == 0:
        return 1.0
    allowed_bad = (1.0 - slo_target) * total_events
    if allowed_bad <= 0:
        return 0.0
    consumed_bad = total_events - good_events
    remaining = 1.0 - (consumed_bad / allowed_bad)
    return max(0.0, min(1.0, remaining))


def burn_rate(good_events: int, total_events: int, slo_target: float) -> float:
    """consumed_bad / allowed_bad. 1.0 == on pace to exactly exhaust the budget."""
    _validate(good_events, total_events, slo_target)
    if total_events == 0:
        return 0.0
    allowed_bad = (1.0 - slo_target) * total_events
    if allowed_bad <= 0:
        return float("inf")
    consumed_bad = total_events - good_events
    return consumed_bad / allowed_bad


def remaining_budget_from_sli(sli: float, slo_target: float) -> float:
    """Fraction of the error budget still available, from a ratio SLI instead of counts.

    remaining = 1 - (1 - sli) / (1 - slo_target), clamped to [0, 1].

    Raises ValueError for an SLO target outside (0, 1) or an ``sli`` outside [0, 1].
    """
    if not 0.0 < slo_target < 1.0:
        raise ValueError("slo_target must be strictly between 0 and 1")
    if not 0.0 <= sli <= 1.0:
        raise ValueError(f"sli must be between 0 and 1, got {sli}")
    return max(0.0, min(1.0, 1.0 - (1.0 - sli) / (1.0 - slo_target)))
