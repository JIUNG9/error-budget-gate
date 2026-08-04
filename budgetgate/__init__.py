"""budgetgate — an error-budget gate for automated remediation.

Automation may propose the fix; the error budget decides whether it acts.
"""

from .actions import is_reversible
from .budget import burn_rate, remaining_budget
from .dryrun import dry_run
from .gate import evaluate
from .models import Action, DryRunResult, GateDecision, Service, Tier

__version__ = "0.1.0a1"
__all__ = [
    "evaluate",
    "dry_run",
    "remaining_budget",
    "burn_rate",
    "is_reversible",
    "Action",
    "Service",
    "Tier",
    "GateDecision",
    "DryRunResult",
    "__version__",
]
