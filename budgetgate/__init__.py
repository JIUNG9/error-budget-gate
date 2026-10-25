"""budgetgate — an error-budget gate for automated remediation.

Automation may propose the fix; the error budget decides whether it acts.
"""

from .actions import is_reversible
from .budget import burn_rate, remaining_budget, remaining_budget_from_sli
from .dryrun import dry_run
from .gate import evaluate
from .models import Action, DryRunResult, GateDecision, Service, Tier
from .prometheus import PrometheusError, remaining_budget_from_prometheus

__version__ = "0.1.0a1"
__all__ = [
    "evaluate",
    "dry_run",
    "remaining_budget",
    "remaining_budget_from_sli",
    "remaining_budget_from_prometheus",
    "PrometheusError",
    "burn_rate",
    "is_reversible",
    "Action",
    "Service",
    "Tier",
    "GateDecision",
    "DryRunResult",
    "__version__",
]
