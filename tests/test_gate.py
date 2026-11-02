import pytest

from budgetgate import Action, Service, Tier, dry_run, evaluate


def _act(name="restart", reversible=True, dur=30):
    return Action(name=name, reversible=reversible, est_duration_s=dur)


def test_allow_reversible_healthy_budget_nonprod():
    d = evaluate(_act(), Service("checkout", Tier.TIER_2), budget_remaining=0.8, env="dev")
    assert d.allow and not d.requires_human


def test_block_irreversible():
    d = evaluate(_act("delete_pvc", reversible=True), Service("checkout"), 0.9, "dev")
    assert not d.allow and not d.requires_human
    assert "not a reversible" in d.reason


def test_block_when_budget_exhausted():
    d = evaluate(_act(), Service("checkout"), budget_remaining=0.0, env="dev")
    assert not d.allow and d.requires_human
    assert "exhausted" in d.reason


def test_require_human_in_prod():
    d = evaluate(_act(), Service("checkout", Tier.TIER_2), budget_remaining=0.9, env="prod")
    assert not d.allow and d.requires_human


def test_require_human_low_budget_nonprod():
    d = evaluate(_act(), Service("checkout"), budget_remaining=0.10, env="dev")
    assert not d.allow and d.requires_human
    assert "low" in d.reason


def test_tier0_prod_blocks_to_human():
    d = evaluate(_act(), Service("payments", Tier.TIER_0), budget_remaining=0.9, env="prod")
    assert not d.allow and d.requires_human
    assert "tier-0" in d.reason


def test_flag_lies_allowlist_wins():
    # caller claims reversible=True but the name is destructive -> still blocked
    d = evaluate(_act("destroy_cluster", reversible=True), Service("checkout"), 0.9, "dev")
    assert not d.allow


def test_dry_run_no_side_effects():
    r = dry_run(_act("rollout_restart"), Service("checkout"))
    assert r.reversible and r.rollback_available and r.est_duration_s == 30


@pytest.mark.parametrize(
    "name,flag", [("rollout_restart", True), ("rollout_restart", False), ("delete_pvc", True)]
)
def test_dry_run_reversible_matches_the_gate(name, flag):
    # dry_run previews the same reversibility rule evaluate applies: the flag AND the allow-list.
    act = _act(name, reversible=flag)
    r = dry_run(act, Service("checkout"))
    d = evaluate(act, Service("checkout"), 0.9, "dev")
    assert r.reversible == d.allow
    assert r.rollback_available == r.reversible
    assert ("NOT reversible" in r.note) == (not r.reversible)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("env", ["dev", "prod"])
def test_non_finite_budget_never_allows(bad, env):
    # NaN compares False against everything, so without an explicit check it
    # would skip every guard and reach ALLOW.
    d = evaluate(_act(), Service("checkout"), budget_remaining=bad, env=env)
    assert not d.allow and d.requires_human
    assert "unknown" in d.reason


def test_non_finite_budget_does_not_mask_irreversible_block():
    d = evaluate(_act("delete_pvc"), Service("checkout"), float("nan"), "dev")
    assert not d.allow and not d.requires_human


@pytest.mark.parametrize("env", ["production", "prd", "prod-eu", "", "  ", None])
def test_unknown_env_is_not_treated_as_non_prod(env):
    d = evaluate(_act(), Service("checkout"), budget_remaining=0.9, env=env)
    assert not d.allow and d.requires_human
    assert "unknown env" in d.reason


@pytest.mark.parametrize(
    "env", ["dev", "Development", " STAGING ", "qa", "test", "sandbox", "local"]
)
def test_known_non_prod_envs_still_allow(env):
    d = evaluate(_act(), Service("checkout"), budget_remaining=0.9, env=env)
    assert d.allow and not d.requires_human


def test_unknown_env_tier0_blocks_to_human():
    d = evaluate(_act(), Service("payments", Tier.TIER_0), budget_remaining=0.9, env="production")
    assert not d.allow and d.requires_human
    assert "tier-0" in d.reason


def test_prod_env_is_case_and_space_insensitive():
    d = evaluate(_act(), Service("checkout"), budget_remaining=0.9, env=" PROD ")
    assert not d.allow and d.requires_human
    assert "production action" in d.reason


def test_budget_above_one_requires_human():
    d = evaluate(_act(), Service("checkout"), budget_remaining=5.0, env="dev")
    assert not d.allow and d.requires_human
    assert "above 1" in d.reason


def test_custom_non_prod_env_can_allow():
    d = evaluate(_act(), Service("checkout"), 0.8, env="preprod", non_prod_envs=["preprod", "Dev"])
    assert d.allow


def test_custom_set_replaces_the_default():
    d = evaluate(_act(), Service("checkout"), 0.8, env="dev", non_prod_envs=["preprod"])
    assert not d.allow and d.requires_human


def test_custom_set_is_case_and_space_insensitive():
    d = evaluate(_act(), Service("checkout"), 0.8, env=" PreProd ", non_prod_envs=[" PREPROD"])
    assert d.allow


@pytest.mark.parametrize("bad", [["prod"], ["Production"], ["dev", " PROD "]])
def test_custom_set_cannot_include_prod(bad):
    with pytest.raises(ValueError, match="production"):
        evaluate(_act(), Service("checkout"), 0.8, env="dev", non_prod_envs=bad)


def test_custom_set_rejects_empty_name():
    with pytest.raises(ValueError, match="empty"):
        evaluate(_act(), Service("checkout"), 0.8, env="dev", non_prod_envs=["dev", ""])


def test_custom_set_rejects_a_bare_string():
    with pytest.raises(TypeError):
        evaluate(_act(), Service("checkout"), 0.8, env="preprod", non_prod_envs="preprod")


def test_empty_custom_set_allows_nothing():
    d = evaluate(_act(), Service("checkout"), 0.8, env="dev", non_prod_envs=[])
    assert not d.allow and d.requires_human


# --- burn rate (SRE Workbook thresholds: 14.4x over 1h blocks, 6x over 6h needs a human) ---


def _burn(**kw):
    return evaluate(_act(), Service("checkout", Tier.TIER_2), 0.8, "dev", **kw)


def test_burn_rates_default_to_no_effect():
    assert _burn().allow


@pytest.mark.parametrize("value", [0, 1, 14.39])
def test_1h_burn_below_threshold_allows(value):
    assert _burn(burn_rate_1h=value).allow


@pytest.mark.parametrize("value", [14.4, 14.41, 100, float("inf")])
def test_1h_burn_at_or_above_threshold_blocks(value):
    d = _burn(burn_rate_1h=value)
    assert not d.allow and d.requires_human
    assert d.reason.startswith("BLOCK")


@pytest.mark.parametrize("value", [0, 1, 5.99])
def test_6h_burn_below_threshold_allows(value):
    assert _burn(burn_rate_6h=value).allow


@pytest.mark.parametrize("value", [6, 6.01, 14.39, 50])
def test_6h_burn_at_or_above_threshold_requires_human(value):
    d = _burn(burn_rate_6h=value)
    assert not d.allow and d.requires_human
    assert d.reason.startswith("REQUIRE_HUMAN")


def test_each_window_uses_only_its_own_threshold():
    # 1h burn of 10 is below 14.4; 6h burn of 3 is below 6. Neither trips the other's rule.
    assert _burn(burn_rate_1h=10, burn_rate_6h=3).allow
    # A 1h value above the 6h threshold does not trip the 6h rule.
    assert _burn(burn_rate_1h=7).allow


def test_1h_block_wins_over_6h_require_human():
    d = _burn(burn_rate_1h=20, burn_rate_6h=7)
    assert d.reason.startswith("BLOCK")


@pytest.mark.parametrize("kw", [{"burn_rate_1h": float("nan")}, {"burn_rate_6h": float("nan")}])
def test_nan_burn_rate_requires_human(kw):
    d = _burn(**kw)
    assert not d.allow and d.requires_human
    assert d.reason.startswith("REQUIRE_HUMAN")


@pytest.mark.parametrize("kw", [{"burn_rate_1h": -0.1}, {"burn_rate_6h": -1}])
def test_negative_burn_rate_is_rejected(kw):
    with pytest.raises(ValueError):
        _burn(**kw)


@pytest.mark.parametrize("bad", ["5", True])
def test_non_numeric_burn_rate_is_rejected(bad):
    with pytest.raises(TypeError):
        _burn(burn_rate_1h=bad)


def test_burn_rate_does_not_mask_an_irreversible_block():
    d = evaluate(_act("delete_pvc"), Service("checkout"), 0.9, "dev", burn_rate_6h=7)
    assert "not a reversible" in d.reason


def test_burn_rate_blocks_in_prod_too():
    d = evaluate(_act(), Service("checkout", Tier.TIER_2), 0.9, "prod", burn_rate_1h=15)
    assert d.reason.startswith("BLOCK")
