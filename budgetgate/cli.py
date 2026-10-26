"""Command line entry point: `python -m budgetgate`.

Prints the gate's decision and exits 0 (allow), 10 (require human) or 20 (block), so a
shell script or CI job can branch on `$?` without parsing text.
"""

import argparse
import json
import sys
from collections.abc import Sequence

from .gate import evaluate
from .models import Action, GateDecision, Service, Tier

EXIT_ALLOW = 0
EXIT_REQUIRE_HUMAN = 10
EXIT_BLOCK = 20


def exit_code(decision: GateDecision) -> int:
    """Map a decision to an exit code. A reason starting with BLOCK is a block."""
    if decision.allow:
        return EXIT_ALLOW
    if decision.reason.startswith("BLOCK"):
        return EXIT_BLOCK
    return EXIT_REQUIRE_HUMAN


def _tier(value: str) -> Tier:
    try:
        return Tier(int(value))
    except ValueError:
        raise argparse.ArgumentTypeError(f"tier must be 0, 1, 2 or 3, got {value!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budgetgate",
        description="Decide whether an automated action may run unattended.",
        epilog="exit codes: 0 allow, 10 require human, 20 block, 2 bad arguments",
    )
    parser.add_argument("--action", required=True, help="action name, e.g. rollout_restart")
    parser.add_argument("--service", required=True, help="service the action targets")
    parser.add_argument(
        "--budget",
        required=True,
        type=float,
        help="remaining error budget as a fraction (0.5 = 50%% left); nan requires a human",
    )
    parser.add_argument("--env", default="dev", help="environment name (default: dev)")
    parser.add_argument(
        "--tier", type=_tier, default=Tier.TIER_2, help="service tier 0-3 (default: 2)"
    )
    parser.add_argument("--json", action="store_true", help="print the decision as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # The allow-list in is_reversible() decides reversibility; the flag cannot widen it.
    action = Action(args.action, reversible=True)
    decision = evaluate(action, Service(args.service, tier=args.tier), args.budget, args.env)
    code = exit_code(decision)
    if args.json:
        payload = {
            "allow": decision.allow,
            "requires_human": decision.requires_human,
            "reason": decision.reason,
            "exit_code": code,
        }
        print(json.dumps(payload))
    else:
        print(decision.reason)
    return code


if __name__ == "__main__":
    sys.exit(main())
