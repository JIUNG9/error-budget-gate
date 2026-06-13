"""Core data types for budgetgate. All frozen + pure — no I/O."""
from dataclasses import dataclass
from enum import IntEnum


class Tier(IntEnum):
    """Service criticality. Lower = more critical."""
    TIER_0 = 0  # revenue-critical / customer-facing core
    TIER_1 = 1  # important, user-visible
    TIER_2 = 2  # internal, degradable
    TIER_3 = 3  # sandbox / dev


@dataclass(frozen=True)
class Action:
    """An automated action a remediation system wants to take."""
    name: str
    reversible: bool = False
    est_duration_s: int = 0


@dataclass(frozen=True)
class Service:
    name: str
    tier: Tier = Tier.TIER_2
    slo_target: float = 0.999
    window_days: int = 28


@dataclass(frozen=True)
class GateDecision:
    """allow = may the automation proceed UNATTENDED?
    requires_human = should a human be paged / approve?"""
    allow: bool
    requires_human: bool
    reason: str


@dataclass(frozen=True)
class DryRunResult:
    action: str
    service: str
    reversible: bool
    rollback_available: bool
    est_duration_s: int
    note: str
