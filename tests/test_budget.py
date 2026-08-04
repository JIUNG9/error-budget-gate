import pytest

from budgetgate import burn_rate, remaining_budget


def test_full_budget_when_no_bad_events():
    assert remaining_budget(good_events=1000, total_events=1000, slo_target=0.99) == 1.0


def test_half_budget_consumed():
    # 99% target on 1000 => 10 allowed bad. 5 bad => 50% remaining.
    assert remaining_budget(good_events=995, total_events=1000, slo_target=0.99) == pytest.approx(
        0.5
    )


def test_budget_exhausted_clamps_to_zero():
    # 20 bad against 10 allowed => clamps to 0, not negative.
    assert remaining_budget(good_events=980, total_events=1000, slo_target=0.99) == 0.0


def test_no_traffic_means_full_budget():
    assert remaining_budget(0, 0, 0.99) == 1.0


def test_burn_rate_on_pace():
    # consuming exactly the allowed bad => burn rate 1.0
    assert burn_rate(good_events=990, total_events=1000, slo_target=0.99) == pytest.approx(1.0)


def test_burn_rate_double():
    assert burn_rate(good_events=980, total_events=1000, slo_target=0.99) == pytest.approx(2.0)


def test_invalid_slo_raises():
    import pytest

    with pytest.raises(ValueError):
        remaining_budget(1, 1, 1.0)
