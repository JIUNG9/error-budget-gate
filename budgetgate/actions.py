"""The reversible-action allow-list. Anything destructive is never reversible."""

REVERSIBLE_ACTIONS = frozenset({
    "restart",
    "rollout_restart",
    "scale_up_1",
    "scale_down_1",
    "clear_queue",
    "drain_node",
    "failover",
})

DESTRUCTIVE_TOKENS = ("delete", "destroy", "drop", "terminate", "wipe", "purge")


def is_reversible(action_name: str) -> bool:
    name = action_name.lower().strip()
    if any(tok in name for tok in DESTRUCTIVE_TOKENS):
        return False
    return name in REVERSIBLE_ACTIONS
