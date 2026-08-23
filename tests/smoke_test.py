"""Smoke tests for the DALE Kernel foundation and WT-001 pipeline."""

import sys
import uuid

from src.dale_kernel.core.canons import (
    AbstractInput,
    ARAOutput,
    ECOAOutput,
    EngagementType,
    FormalDALEResult,
    FundamentalVariable,
    ObservationCondition,
    ObservationMode,
    ObservationPackage,
    VariableState,
)
from src.dale_kernel.core.engine import DALEKernel
from src.dale_kernel.services.admissibility import AdmissibilityEngine
from src.dale_kernel.services.event_store import EventStore, EventType
from src.dale_kernel.services.input_formation import (
    FormedInput,
    FormationStatus,
    InputFormationService,
)
from src.dale_kernel.services.state_resolver import StateResolver
from src.dale_kernel.services.traceability import TraceabilityFactory


def test_admissibility_logic():
    engine = AdmissibilityEngine()
    condition = ObservationCondition(
        sector="test", geography="test-location",
        engagement_type=EngagementType.LEVEL3_PLATFORM,
        observation_mode=ObservationMode.MIXED,
    )
    valid_package = ObservationPackage(
        walkthrough_id="WT-001", scenario_type="Baseline",
        inputs=[AbstractInput(source_actor="ActorA", content={"arch_frame": "P1", "key": "value"})],
        observation_condition=condition,
    )
    is_valid, results = engine.validate_package(valid_package)
    assert is_valid is True, results

    invalid_package = ObservationPackage(
        walkthrough_id="WT-001", scenario_type="Baseline",
        inputs=[AbstractInput(source_actor="ActorB", content={"external_api": "hack"})],
        observation_condition=condition,
    )
    is_valid, results = engine.validate_package(invalid_package)
    assert is_valid is False
    assert results[0]["rule"] == 3


def test_traceability_logic():
    factory = TraceabilityFactory()
    root = factory.create_root_trace(condition_id="COND-001")
    child = factory.create_child_trace(parent=root, variable_ids=["v1"])
    variable = FundamentalVariable(
        variable_id="v1", variable_name="Identity", value=0.5,
        state=VariableState.ECOA_FIXED,
    )
    factory.link_variable_to_trace(variable, child)
    assert root.trace_type == "root"
    assert child.parent_trace_id == root.trace_id
    assert child.trace_id in variable.linked_trace_ids


def test_variable_states():
    fixed = FundamentalVariable(variable_id="v1", variable_name="Identity", value=0.5, state=VariableState.ECOA_FIXED)
    unresolved = FundamentalVariable(variable_id="v2", variable_name="Dignity", state=VariableState.NON_ASSIGNED)
    resolved = FundamentalVariable(variable_id="v3", variable_name="Agency", value=0.3, state=VariableState.ARA_RESOLVED)
    inactive = FundamentalVariable(variable_id="v4", variable_name="Safety", state=VariableState.STRUCTURALLY_INACTIVE)
    absent = FundamentalVariable(variable_id="v5", variable_name="Readiness", state=VariableState.INFORMATIONAL_ABSENCE)
    assert fixed.is_ecoa_fixed and fixed.value == 0.5
    assert unresolved.is_non_assigned and unresolved.value is None
    assert resolved.is_ara_resolved
    assert inactive.is_inactive
    assert absent.value is None


def test_ecoa_output_partition():
    condition = ObservationCondition(sector="test", geography="test")
    variables = [
        FundamentalVariable(variable_id="v1", variable_name="Identity", value=0.5, state=VariableState.ECOA_FIXED),
        FundamentalVariable(variable_id="v2", variable_name="Dignity", state=VariableState.NON_ASSIGNED),
        FundamentalVariable(variable_id="v3", variable_name="Agency", value=0.3, state=VariableState.ECOA_FIXED),
    ]
    output = ECOAOutput(
        package_id="pkg-001", observation_condition=condition,
        fundamental_state=variables,
        assigned_variables=["v1", "v3"], non_assigned_variables=["v2"],
    )
    assert output.has_non_assigned is True
    assert set(output.assigned_variables).isdisjoint(output.non_assigned_variables)


def test_formal_result():
    condition = ObservationCondition(sector="test", geography="test")
    ecoa = ECOAOutput(
        package_id="pkg-001", observation_condition=condition,
        fundamental_state=[
            FundamentalVariable(variable_id="v1", variable_name="Identity", value=0.5, state=VariableState.ECOA_FIXED),
            FundamentalVariable(variable_id="v2", variable_name="Dignity", state=VariableState.NON_ASSIGNED),
        ],
        assigned_variables=["v1"], non_assigned_variables=["v2"],
    )
    ara = ARAOutput(
        ecoa_observation_id=ecoa.observation_id,
        ecoa_fixed_variables=[v for v in ecoa.fundamental_state if v.is_ecoa_fixed],
        completion_field=["v2"], completed_values={"v2": 0.7},
        solution_unique=True, solver_status="optimal",
    )
    result = FormalDALEResult(ecoa_output=ecoa, ara_output=ara)
    assert result.is_complete is True
    assert result.variable_summary["ecoa_fixed"] == 1
    assert result.variable_summary["ara_resolved"] == 1


def test_event_store():
    store = EventStore(f"WT-001-TEST-{uuid.uuid4().hex[:8]}")
    assert store.event_count == 0
    first_id = store.append(EventType.OBSERVATION_STARTED, {"test": True})
    store.append(EventType.VARIABLE_ASSIGNED, {"variable_id": "v1", "value": 0.5})
    assert first_id.startswith("evt-WT-001-TEST-")
    assert store.event_count == 2
    assert len(store.read_all()) == 2
    assert store.last_event()["payload"]["variable_id"] == "v1"


def make_baseline_package() -> ObservationPackage:
    condition = ObservationCondition(
        sector="test", geography="test-location",
        engagement_type=EngagementType.LEVEL3_PLATFORM,
        observation_mode=ObservationMode.MIXED,
    )
    return ObservationPackage(
        walkthrough_id="WT-001", scenario_type="Baseline",
        inputs=[AbstractInput(source_actor="TestActor", content={"arch_frame": "P1", "key": "value"})],
        observation_condition=condition,
    )


def test_wt001_pipeline():
    kernel = DALEKernel("WT-001")
    result, errors = kernel.execute(make_baseline_package(), StateResolver.make_coherent_variables(count=5))
    assert errors == []
    assert result is not None
    assert result.is_complete is True
    assert result.ara_output is None
    assert len(result.ecoa_output.assigned_variables) == 5
    assert result.ecoa_output.non_assigned_variables == []
    assert kernel.event_count > 0
    assert kernel.current_state.value == "coherent"


def test_wt001_rejects_invalid_input():
    invalid = make_baseline_package().model_copy(update={
        "inputs": [AbstractInput(source_actor="BadActor", content={"external_api": "hack"})],
    })
    result, errors = DALEKernel("WT-001").execute(invalid, StateResolver.make_coherent_variables(count=5))
    assert result is None
    assert errors[0]["rule"] == 3


def test_input_formation_valid():
    """Test that valid source information produces a FORMED input."""
    service = InputFormationService()
    source = {
        "goal": "Learn new farming techniques to improve crop yield",
        "blockers": ["Limited access to training materials"],
        "aspiration_text": "I want to become a model farmer in my community and train others",
        "county": "Kisumu",
        "ward": "Central",
        "age_range": "25-34",
        "work_type": "self_employed",
    }
    formed, traces = service.form_input(
        session_id="sess-001",
        user_id="user-001",
        source=source,
    )
    assert formed.formation_status == FormationStatus.FORMED
    assert formed.goal == "Learn new farming techniques to improve crop yield"
    assert len(formed.blockers) == 1
    assert formed.county == "Kisumu"
    assert formed.ward == "Central"
    assert formed.no_invented_values is True
    assert formed.missing_required_fields == []
    assert len(traces) >= 2  # root + child


def test_input_formation_missing_required():
    """Test that missing required fields produce INSUFFICIENT_INFORMATION."""
    service = InputFormationService()
    source = {
        "goal": "Start a business",
        # county and ward missing
        "blockers": [],
    }
    formed, traces = service.form_input(
        session_id="sess-002",
        user_id="user-002",
        source=source,
    )
    assert formed.formation_status == FormationStatus.INSUFFICIENT_INFORMATION
    assert "county" in formed.missing_required_fields
    assert "ward" in formed.missing_required_fields
    assert formed.no_invented_values is True  # didn't make up county/ward


def test_input_formation_ambiguity_detection():
    """Test that contradictory goal-blocker combos are flagged."""
    service = InputFormationService()
    source = {
        "goal": "Start a business",
        "blockers": ["No capital", "No access to funds"],
        "aspiration_text": "Start a business",
        "county": "Nairobi",
        "ward": "Westlands",
    }
    formed, traces = service.form_input(
        session_id="sess-003",
        user_id="user-003",
        source=source,
    )
    assert formed.formation_status == FormationStatus.AMBIGUITY_PRESERVED
    assert len(formed.unresolved_ambiguities) > 0
    assert any("resources" in a for a in formed.unresolved_ambiguities)


def test_input_formation_to_abstract_input():
    """Test conversion from FormedInput to AbstractInput."""
    service = InputFormationService()
    source = {
        "goal": "Expand my farm",
        "county": "Kisumu",
        "ward": "Central",
    }
    formed, _ = service.form_input("sess-004", "user-004", source)
    abstract = service.to_abstract_input(formed)
    assert abstract.source_actor == "user:user-004"
    assert abstract.content["goal"] == "Expand my farm"
    assert abstract.content["_formation_status"] == "formed"


def test_input_formation_to_observation_package():
    """Test full conversion chain: source → FormedInput → ObservationPackage."""
    service = InputFormationService()
    source = {
        "goal": "Learn new farming techniques",
        "blockers": ["No internet access"],
        "county": "Kisumu",
        "ward": "Central",
    }
    formed, _ = service.form_input("sess-005", "user-005", source)
    package = service.to_observation_package(formed, walkthrough_id="WT-001")
    assert package.walkthrough_id == "WT-001"
    assert package.scenario_type == "jielekeze"
    assert len(package.inputs) == 1
    assert package.inputs[0].content["goal"] == "Learn new farming techniques"


def test_input_formation_no_invention():
    """Guardrail: absent fields must not be invented."""
    service = InputFormationService()
    source = {
        "goal": "Test goal",
        "county": "Kisumu",
        "ward": "Central",
        # age_range and work_type intentionally absent
    }
    formed, _ = service.form_input("sess-006", "user-006", source)
    assert formed.age_range is None
    assert formed.work_type is None
    assert formed.no_invented_values is True


def main() -> int:
    tests = [
        ("Admissibility Engine", test_admissibility_logic),
        ("Traceability Factory", test_traceability_logic),
        ("Variable States", test_variable_states),
        ("ECOA Output Partition", test_ecoa_output_partition),
        ("Formal DALE Result", test_formal_result),
        ("Event Store", test_event_store),
        ("WT-001 Pipeline", test_wt001_pipeline),
        ("WT-001 Rejects Invalid Input", test_wt001_rejects_invalid_input),
        ("Input Formation — Valid", test_input_formation_valid),
        ("Input Formation — Missing Required", test_input_formation_missing_required),
        ("Input Formation — Ambiguity Detection", test_input_formation_ambiguity_detection),
        ("Input Formation — To AbstractInput", test_input_formation_to_abstract_input),
        ("Input Formation — To ObservationPackage", test_input_formation_to_observation_package),
        ("Input Formation — No Invention Guardrail", test_input_formation_no_invention),
    ]
    passed = 0
    for name, test in tests:
        test()
        sys.stdout.write(f"  PASS  {name}\n")
        passed += 1
    sys.stdout.write(f"\n{passed} passed, 0 failed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())