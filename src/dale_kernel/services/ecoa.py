"""Formal ECOA Stage 1 partition boundary.

This module implements state machinery, not domain-specific ECOA mathematics.
Assignment values can only come from an explicitly supplied ObservationRule.
"""

from enum import Enum
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from ..core.canons import (
    ECOAOutput,
    FundamentalVariable,
    ObservationPackage,
    ValueOrigin,
    VariableState,
)


class PartitionState(str, Enum):
    NOT_ACTIVE = "not_active"
    ACTIVE_ASSIGNED = "active_assigned"
    ACTIVE_NON_ASSIGNED = "active_non_assigned"
    INFORMATIONAL_ABSENCE = "informational_absence"


class VariableDefinition(BaseModel):
    """Architecture registry entry controlling whether a variable is active."""

    variable_id: str
    variable_name: str
    active: bool = True


class AssignmentDecision(BaseModel):
    """Result of a declared observation rule for one variable."""

    state: PartitionState
    value: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    reason: str
    evidence_refs: List[str] = Field(default_factory=list)


class ObservationRule(Protocol):
    """Rule interface for adaptation-owned ECOA assignment derivation."""

    def derive(
        self,
        variable_definition: VariableDefinition,
        observation_package: ObservationPackage,
    ) -> AssignmentDecision:
        ...


class ECOAObservationResult(BaseModel):
    """Explicit Stage 1 partition and traceable variable result."""

    package_id: str
    assigned_variables: List[FundamentalVariable] = Field(default_factory=list)
    non_assigned_variables: List[FundamentalVariable] = Field(default_factory=list)
    inactive_variables: List[FundamentalVariable] = Field(default_factory=list)
    informational_absence_variables: List[FundamentalVariable] = Field(default_factory=list)
    structural_insufficiency: List[str] = Field(default_factory=list)
    trace_path: List[str] = Field(default_factory=list)
    completed: bool = False

    @property
    def completion_field(self) -> List[str]:
        return [variable.variable_id for variable in self.non_assigned_variables]

    @property
    def ara_required(self) -> bool:
        return bool(self.completion_field) and not self.structural_insufficiency

    @property
    def partition_ids(self) -> Dict[PartitionState, List[str]]:
        return {
            PartitionState.ACTIVE_ASSIGNED: [v.variable_id for v in self.assigned_variables],
            PartitionState.ACTIVE_NON_ASSIGNED: [v.variable_id for v in self.non_assigned_variables],
            PartitionState.NOT_ACTIVE: [v.variable_id for v in self.inactive_variables],
            PartitionState.INFORMATIONAL_ABSENCE: [v.variable_id for v in self.informational_absence_variables],
        }

    def validate_partition(self, expected_ids: List[str]) -> None:
        """Reject incomplete or overlapping partition membership."""
        partition_lists = list(self.partition_ids.values())
        flattened = [variable_id for group in partition_lists for variable_id in group]
        if len(flattened) != len(set(flattened)):
            raise ValueError("ECOA partition contains overlapping variable states")
        if set(flattened) != set(expected_ids):
            raise ValueError("ECOA partition does not cover every registered variable")

    def to_output(self, package: ObservationPackage) -> ECOAOutput:
        """Convert the partition into the existing formal ECOA output model."""
        return ECOAOutput(
            observation_id=f"ecoa:{self.package_id}",
            package_id=self.package_id,
            observation_condition=package.observation_condition,
            adaptation_ref=package.adaptation_ref,
            version=package.version,
            fundamental_state=[
                *self.assigned_variables,
                *self.non_assigned_variables,
                *self.inactive_variables,
                *self.informational_absence_variables,
            ],
            assigned_variables=[v.variable_id for v in self.assigned_variables],
            non_assigned_variables=[v.variable_id for v in self.non_assigned_variables],
            trace_path=self.trace_path,
        )


class ECOAObservationService:
    """Apply declared observation rules and produce an explicit partition."""

    def observe(
        self,
        package: ObservationPackage,
        variable_definitions: List[VariableDefinition],
        rules: Dict[str, ObservationRule],
        trace_path: Optional[List[str]] = None,
    ) -> ECOAObservationResult:
        assigned: List[FundamentalVariable] = []
        non_assigned: List[FundamentalVariable] = []
        inactive: List[FundamentalVariable] = []
        informational_absence: List[FundamentalVariable] = []
        insufficiency: List[str] = []

        for definition in variable_definitions:
            if not definition.active:
                inactive.append(FundamentalVariable(
                    variable_id=definition.variable_id,
                    variable_name=definition.variable_name,
                    state=VariableState.STRUCTURALLY_INACTIVE,
                ))
                continue

            rule = rules.get(definition.variable_id)
            if rule is None:
                non_assigned.append(FundamentalVariable(
                    variable_id=definition.variable_id,
                    variable_name=definition.variable_name,
                    state=VariableState.NON_ASSIGNED,
                ))
                continue

            decision = rule.derive(definition, package)
            if not decision.reason:
                raise ValueError(f"Observation decision for {definition.variable_id} has no reason")

            if decision.state == PartitionState.ACTIVE_ASSIGNED:
                if decision.value is None:
                    raise ValueError(f"Assigned decision for {definition.variable_id} has no value")
                assigned.append(FundamentalVariable(
                    variable_id=definition.variable_id,
                    variable_name=definition.variable_name,
                    value=decision.value,
                    state=VariableState.ECOA_FIXED,
                    value_origin=ValueOrigin.ECOA_ASSIGNED,
                ))
            elif decision.state == PartitionState.ACTIVE_NON_ASSIGNED:
                non_assigned.append(FundamentalVariable(
                    variable_id=definition.variable_id,
                    variable_name=definition.variable_name,
                    state=VariableState.NON_ASSIGNED,
                ))
            elif decision.state == PartitionState.INFORMATIONAL_ABSENCE:
                informational_absence.append(FundamentalVariable(
                    variable_id=definition.variable_id,
                    variable_name=definition.variable_name,
                    state=VariableState.INFORMATIONAL_ABSENCE,
                ))
            elif decision.state == PartitionState.NOT_ACTIVE:
                raise ValueError(f"Inactivity for {definition.variable_id} must come from the variable registry")

        result = ECOAObservationResult(
            package_id=package.package_id,
            assigned_variables=assigned,
            non_assigned_variables=non_assigned,
            inactive_variables=inactive,
            informational_absence_variables=informational_absence,
            structural_insufficiency=insufficiency,
            trace_path=trace_path or [f"package:{package.package_id}"],
            completed=True,
        )
        result.validate_partition([definition.variable_id for definition in variable_definitions])
        return result