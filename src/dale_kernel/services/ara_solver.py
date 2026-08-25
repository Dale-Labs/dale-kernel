"""Specification-driven ARA Stage 2 completion framework.

This module provides the boundary and result semantics for ARA. It does not
choose anchors, penalties, constraints, or reconstruction functions.
"""

from typing import Callable, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from ..core.canons import FundamentalVariable, ValueOrigin
from .ara_gate import ARAReadiness, ARAReadinessDecision
from .ecoa import ECOAObservationResult


class ARAConfiguration(BaseModel):
    """Adaptation-owned ARA configuration; fields are required for solving."""

    anchors: Dict[str, float] = Field(default_factory=dict)
    domain_description: Optional[str] = None
    architecture_penalty_ref: Optional[str] = None
    reconstruction_penalty_ref: Optional[str] = None
    reconstruction_ref: Optional[str] = None
    design_package_ref: Optional[str] = None
    uniqueness_policy: Optional[str] = None

    def missing_requirements(self, completion_field: List[str]) -> List[str]:
        missing = []
        if any(variable_id not in self.anchors for variable_id in completion_field):
            missing.append("anchors for every completion-field variable")
        if not self.domain_description:
            missing.append("admissible domain")
        if not self.architecture_penalty_ref:
            missing.append("architecture penalty")
        if not self.reconstruction_penalty_ref:
            missing.append("reconstruction penalty")
        if not self.reconstruction_ref:
            missing.append("reconstruction function")
        if not self.design_package_ref:
            missing.append("Stage 2 design package")
        if not self.uniqueness_policy:
            missing.append("uniqueness policy")
        return missing


class ARASolver(Protocol):
    """Adaptation-owned solver interface."""

    def solve(
        self,
        fixed_variables: List[FundamentalVariable],
        completion_field: List[str],
        configuration: ARAConfiguration,
    ) -> Dict[str, float]:
        ...


class ARAFrameworkResult(BaseModel):
    """Transparent ARA outcome, including blocked/specification-incomplete states."""

    status: ARAReadiness
    solver_status: str
    reason: str
    completion_field: List[str] = Field(default_factory=list)
    completed_values: Dict[str, float] = Field(default_factory=dict)
    fixed_variable_ids: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    value_origins: Dict[str, ValueOrigin] = Field(default_factory=dict)


class ARACompletionFramework:
    """Run an adaptation-provided solver only after the gate and config pass."""

    def execute(
        self,
        ecoa: ECOAObservationResult,
        readiness: ARAReadinessDecision,
        configuration: ARAConfiguration,
        solver: Optional[ARASolver] = None,
    ) -> ARAFrameworkResult:
        fixed_ids = [variable.variable_id for variable in ecoa.assigned_variables]
        if readiness.status == ARAReadiness.ARA_NOT_REQUIRED:
            return ARAFrameworkResult(
                status=readiness.status,
                solver_status="not_required",
                reason=readiness.reason,
                fixed_variable_ids=fixed_ids,
            )
        if readiness.status == ARAReadiness.ARA_BLOCKED:
            return ARAFrameworkResult(
                status=readiness.status,
                solver_status="blocked",
                reason=readiness.reason,
                completion_field=readiness.completion_field,
                fixed_variable_ids=fixed_ids,
                missing_requirements=readiness.blockers,
            )

        missing = configuration.missing_requirements(readiness.completion_field)
        if missing:
            return ARAFrameworkResult(
                status=ARAReadiness.ARA_BLOCKED,
                solver_status="specification_incomplete",
                reason="ARA adaptation specification is incomplete",
                completion_field=readiness.completion_field,
                fixed_variable_ids=fixed_ids,
                missing_requirements=missing,
            )
        if solver is None:
            return ARAFrameworkResult(
                status=ARAReadiness.ARA_BLOCKED,
                solver_status="solver_not_supplied",
                reason="ARA requires an adaptation-provided solver",
                completion_field=readiness.completion_field,
                fixed_variable_ids=fixed_ids,
            )

        completed_values = solver.solve(
            ecoa.assigned_variables,
            readiness.completion_field,
            configuration,
        )
        if set(completed_values) != set(readiness.completion_field):
            return ARAFrameworkResult(
                status=ARAReadiness.ARA_BLOCKED,
                solver_status="invalid_completion_field",
                reason="solver did not return exactly the inherited completion field",
                completion_field=readiness.completion_field,
                fixed_variable_ids=fixed_ids,
            )
        return ARAFrameworkResult(
            status=ARAReadiness.ARA_READY,
            solver_status="completed",
            reason="adaptation-provided ARA solver completed",
            completion_field=readiness.completion_field,
            completed_values=completed_values,
            fixed_variable_ids=fixed_ids,
            value_origins={variable_id: ValueOrigin.ARA_COMPLETED for variable_id in completed_values},
        )