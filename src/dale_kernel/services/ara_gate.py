"""ECOA-to-ARA Stage 2 transition gate.

The gate decides whether ARA is required, ready, or blocked. It does not solve
the ARA objective and does not invent adaptation-specific constraints.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from .ecoa import ECOAObservationResult


class ARAReadiness(str, Enum):
    ARA_NOT_REQUIRED = "ara_not_required"
    ARA_READY = "ara_ready"
    ARA_BLOCKED = "ara_blocked"


class ARAReadinessDecision(BaseModel):
    status: ARAReadiness
    reason: str
    completion_field: List[str] = Field(default_factory=list)
    fixed_variable_ids: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)


class ARATransitionGate:
    """Validate ECOA completion and inherited state before ARA."""

    def evaluate(
        self,
        ecoa: ECOAObservationResult,
        architecture_available: bool = True,
        inherited_state_sufficient: bool = True,
    ) -> ARAReadinessDecision:
        if not ecoa.completed:
            return ARAReadinessDecision(
                status=ARAReadiness.ARA_BLOCKED,
                reason="ECOA observation has not completed",
                blockers=["ecoa_incomplete"],
            )
        if ecoa.structural_insufficiency:
            return ARAReadinessDecision(
                status=ARAReadiness.ARA_BLOCKED,
                reason="structural insufficiency requires architecture review",
                completion_field=ecoa.completion_field,
                fixed_variable_ids=[v.variable_id for v in ecoa.assigned_variables],
                blockers=list(ecoa.structural_insufficiency),
            )
        if not architecture_available or not inherited_state_sufficient:
            blockers = []
            if not architecture_available:
                blockers.append("inherited_architecture_unavailable")
            if not inherited_state_sufficient:
                blockers.append("inherited_state_insufficient")
            return ARAReadinessDecision(
                status=ARAReadiness.ARA_BLOCKED,
                reason="ECOA state cannot support ARA continuation",
                completion_field=ecoa.completion_field,
                fixed_variable_ids=[v.variable_id for v in ecoa.assigned_variables],
                blockers=blockers,
            )
        if not ecoa.completion_field:
            return ARAReadinessDecision(
                status=ARAReadiness.ARA_NOT_REQUIRED,
                reason="ECOA left no non-assigned variables",
                fixed_variable_ids=[v.variable_id for v in ecoa.assigned_variables],
            )
        return ARAReadinessDecision(
            status=ARAReadiness.ARA_READY,
            reason="ECOA completed with a valid non-assigned completion field",
            completion_field=ecoa.completion_field,
            fixed_variable_ids=[v.variable_id for v in ecoa.assigned_variables],
        )