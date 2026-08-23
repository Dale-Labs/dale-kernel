"""Focused checks for the Project-to-ECOA boundary."""

from src.dale_kernel.core.architecture import (
    ArchitectureStatus,
    BridgeRecord,
    CandidateDecision,
    CandidateDecisionType,
    FormalInputPackage,
    FormalInputStatus,
    ProjectSource,
    RepresentationMode,
    StructuralDeclaration,
)
from src.dale_kernel.core.canons import AbstractInput, ObservationCondition


def make_package(declaration_status: ArchitectureStatus, bridge_status: ArchitectureStatus):
    source = ProjectSource(
        source_type="jielekeze_intake",
        representation=RepresentationMode.NATIVE_STRUCTURED,
        content={"goal": "make_steady_income"},
        source_ref="session:sess_grace_001",
    )
    declaration = StructuralDeclaration(
        source_id=source.source_id,
        structural_class="candidate_abstract",
        active_role="input_candidate",
        representation_mode=RepresentationMode.NATIVE_STRUCTURED,
        architecture_version="jielekeze_v1",
        status=declaration_status,
        formal_keys=["source_id", "observation_condition", "adaptation_ref"],
    )
    bridge = BridgeRecord(
        source_id=source.source_id,
        declaration_id=declaration.declaration_id,
        bridge_type="project_to_ecoa",
        mapping_ref="jielekeze_input_mapping_v1",
        bridge_version="1.0",
        status=bridge_status,
        admitted_input_id="input_grace_001",
        bridge_roles=["observation_support"],
        transformation_refs=["mapping:jielekeze_input_mapping_v1"],
        candidate_decisions=[CandidateDecision(
            candidate_id="input_grace_001",
            decision=CandidateDecisionType.ADMITTED,
            reason="candidate is supported by the declared bridge",
            support_class="formal_input_candidate",
            source_refs=[source.source_id],
            bridge_refs=["mapping:jielekeze_input_mapping_v1"],
        )],
        trace_refs=[f"source:{source.source_id}"],
    )
    return FormalInputPackage(
        source=source,
        declaration=declaration,
        bridge=bridge,
        abstract_input=AbstractInput(source_actor="svc:jielekeze", content=source.content),
        observation_condition=ObservationCondition(sector="jielekeze", geography="nairobi/mathare"),
        adaptation_ref="jielekeze_v1",
        trace_path=[
            f"source:{source.source_id}",
            f"declaration:{declaration.declaration_id}",
            f"bridge:{bridge.bridge_id}",
        ],
    )


def test_open_architecture_requires_review():
    package = make_package(ArchitectureStatus.OPEN, ArchitectureStatus.CLOSED)
    package.close()
    assert package.status == FormalInputStatus.REQUIRES_REVIEW
    assert package.architecture_review.reason == "structural_declaration_not_closed"
    assert package.predicate_results[0].passed is False


def test_closed_declaration_and_bridge_produce_transparent_input():
    package = make_package(ArchitectureStatus.CLOSED, ArchitectureStatus.CLOSED)
    package.close()
    assert package.status == FormalInputStatus.TRANSPARENT
    assert package.reliable_input is True
    assert package.transparent_input is True
    assert all(result.passed for result in package.predicate_results)
    assert package.provenance_refs["bridge_id"] == package.bridge.bridge_id


def test_architecture_review_is_not_non_assignment():
    package = make_package(ArchitectureStatus.REQUIRES_REVIEW, ArchitectureStatus.OPEN)
    package.close()
    assert package.status == FormalInputStatus.REQUIRES_REVIEW
    assert package.architecture_review is not None


def test_duplicate_bridge_roles_require_review():
    package = make_package(ArchitectureStatus.CLOSED, ArchitectureStatus.CLOSED)
    package.bridge.bridge_roles = ["observation_support", "observation_support"]
    package.close()
    assert package.status == FormalInputStatus.REQUIRES_REVIEW
    roles_predicate = next(
        result for result in package.predicate_results
        if result.name.value == "bridge_roles_unique"
    )
    assert roles_predicate.passed is False


if __name__ == "__main__":
    test_open_architecture_requires_review()
    test_closed_declaration_and_bridge_produce_transparent_input()
    test_architecture_review_is_not_non_assignment()
    test_duplicate_bridge_roles_require_review()
    print("4 architecture-boundary checks passed")