"""Pure error-budget math. No I/O — feed it event counts from your SLO source."""


def remaining_budget(good_events: int, total_events: int, slo_target: float) -> float:
    """Fraction of the error budget still available, clamped to [0, 1].

    error budget (allowed bad) = (1 - slo_target) * total_events
    consumed (actual bad)      = total_events - good_events
    remaining fraction         = 1 - consumed / allowed
    """
    if total_events <= 0:
        return 1.0
    if not 0.0 < slo_target < 1.0:
        raise ValueError("slo_target must be strictly between 0 and 1")
    allowed_bad = (1.0 - slo_target) * total_events
    if allowed_bad <= 0:
        return 0.0
    consumed_bad = max(0, total_events - good_events)
    remaining = 1.0 - (consumed_bad / allowed_bad)
    return max(0.0, min(1.0, remaining))


def burn_rate(good_events: int, total_events: int, slo_target: float) -> float:
    """consumed_bad / allowed_bad. 1.0 == on pace to exactly exhaust the budget."""
    if total_events <= 0:
        return 0.0
    if not 0.0 < slo_target < 1.0:
        raise ValueError("slo_target must be strictly between 0 and 1")
    allowed_bad = (1.0 - slo_target) * total_events
    if allowed_bad <= 0:
        return float("inf")
    consumed_bad = max(0, total_events - good_events)
    return consumed_bad / allowed_bad
