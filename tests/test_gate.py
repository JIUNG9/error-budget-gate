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
