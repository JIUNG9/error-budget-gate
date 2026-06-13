from budgetgate import is_reversible


def test_known_reversible():
    assert is_reversible("restart")
    assert is_reversible("rollout_restart")
    assert is_reversible("scale_up_1")


def test_destructive_never_reversible():
    assert not is_reversible("delete_namespace")
    assert not is_reversible("terminate_instance")
    assert not is_reversible("drop_table")


def test_unknown_action_not_reversible():
    assert not is_reversible("frobnicate")


def test_case_insensitive():
    assert is_reversible("RESTART")
