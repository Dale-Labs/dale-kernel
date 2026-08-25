"""Focused ECOA partition and ARA transition/framework tests."""

from src.dale_kernel.core.canons import AbstractInput, ObservationCondition, ObservationPackage, ValueOrigin
from src.dale_kernel.services.ara_gate import ARAReadiness, ARATransitionGate
from src.dale_kernel.services.ara_solver import ARAConfiguration, ARACompletionFramework
from src.dale_kernel.services.ecoa import (
    AssignmentDecision,
    ECOAObservationService,
    PartitionState,
    VariableDefinition,
)


class AssignZero:
    def derive(self, variable_definition, observation_package):
        return AssignmentDecision(
            state=PartitionState.ACTIVE_ASSIGNED,
            value=0.0,
            reason="declared test observation rule",
            evidence_refs=[variable_definition.variable_id],
        )


class InformationallyAbsent:
    def derive(self, variable_definition, observation_package):
        return AssignmentDecision(
            state=PartitionState.INFORMATIONAL_ABSENCE,
            reason="source information unavailable",
        )


def package():
    return ObservationPackage(
        walkthrough_id="WT-001",
        scenario_type="test",
        inputs=[AbstractInput(source_actor="test", content={"arch_frame": "P1"})],
        observation_condition=ObservationCondition(sector="test"),
    )


def test_partition_preserves_active_inactive_and_absence():
    result = ECOAObservationService().observe(
        package(),
        [
            VariableDefinition(variable_id="v1", variable_name="assigned"),
            VariableDefinition(variable_id="v2", variable_name="inactive", active=False),
            VariableDefinition(variable_id="v3", variable_name="absent"),
        ],
        rules={"v1": AssignZero(), "v3": InformationallyAbsent()},
    )
    assert [v.variable_id for v in result.assigned_variables] == ["v1"]
    assert [v.variable_id for v in result.inactive_variables] == ["v2"]
    assert [v.variable_id for v in result.informational_absence_variables] == ["v3"]
    assert result.assigned_variables[0].value == 0.0
    assert result.assigned_variables[0].value_origin == ValueOrigin.ECOA_ASSIGNED


def test_missing_rule_is_non_assigned_not_inactive():
    result = ECOAObservationService().observe(
        package(),
        [VariableDefinition(variable_id="v1", variable_name="unknown")],
        rules={},
    )
    assert result.completion_field == ["v1"]
    assert result.inactive_variables == []


def test_ara_gate_states():
    service = ECOAObservationService()
    assigned = service.observe(package(), [VariableDefinition(variable_id="v1", variable_name="assigned")], {"v1": AssignZero()})
    mixed = service.observe(package(), [VariableDefinition(variable_id="v1", variable_name="assigned"), VariableDefinition(variable_id="v2", variable_name="unknown")], {"v1": AssignZero()})
    gate = ARATransitionGate()
    assert gate.evaluate(assigned).status == ARAReadiness.ARA_NOT_REQUIRED
    assert gate.evaluate(mixed).status == ARAReadiness.ARA_READY
    assert gate.evaluate(mixed, inherited_state_sufficient=False).status == ARAReadiness.ARA_BLOCKED


def test_ara_framework_blocks_without_adaptation_specification():
    service = ECOAObservationService()
    result = service.observe(package(), [VariableDefinition(variable_id="v1", variable_name="unknown")], {})
    readiness = ARATransitionGate().evaluate(result)
    framework = ARACompletionFramework().execute(result, readiness, ARAConfiguration())
    assert framework.status == ARAReadiness.ARA_BLOCKED
    assert framework.solver_status == "specification_incomplete"
    assert "admissible domain" in framework.missing_requirements


if __name__ == "__main__":
    test_partition_preserves_active_inactive_and_absence()
    test_missing_rule_is_non_assigned_not_inactive()
    test_ara_gate_states()
    test_ara_framework_blocks_without_adaptation_specification()
    print("4 ECOA/ARA checks passed")