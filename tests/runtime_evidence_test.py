"""Runtime evidence checks for WT-002 through WT-007 rails."""

from src.dale_kernel.services.runtime_evidence import (
    AdaptationRecord,
    ContradictionRecord,
    GovernanceReviewRecord,
    MemoryReference,
    MissingnessRecord,
    RollbackRecord,
    RuntimeEvidenceBundle,
)


def test_wt002_missingness_is_visible():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-002",
        trace_ids=["WT002-TR-006"],
        missingness=[MissingnessRecord(
            trace_id="WT002-TR-006",
            missingness_type="informational_absence",
            affected_variable_ids=["v15", "X9"],
        )],
    )
    bundle.validate_visibility()
    assert bundle.missingness[0].resolution_status == "unresolved"


def test_wt003_competing_traces_coexist():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-003",
        trace_ids=["WT003-TR-003", "WT003-TR-004"],
        contradictions=[ContradictionRecord(
            contradiction_id="WT003-CON-001",
            trace_ids=["WT003-TR-003", "WT003-TR-004"],
            affected_variable_ids=["v5"],
            contradiction_class="actor_readiness",
        )],
    )
    bundle.validate_visibility()
    assert bundle.contradictions[0].selected_trace_id is None


def test_wt004_governance_review_does_not_signoff():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-004",
        governance_reviews=[GovernanceReviewRecord(
            trace_ids=["WT004-TR-003", "WT004-TR-004"],
            review_questions=["Did governance fractures remain visible?"],
        )],
    )
    bundle.validate_visibility()
    assert bundle.governance_reviews[0].signoff_generated is False


def test_wt005_partial_adaptation_and_rollback_remain_open():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-005",
        adaptations=[AdaptationRecord(parent_trace_ids=["WT005-TR-002"])],
        rollbacks=[RollbackRecord(parent_trace_ids=["WT005-TR-005"])],
    )
    bundle.validate_visibility()
    assert bundle.adaptations[0].full_coherence_claim_allowed is False


def test_wt006_memory_does_not_rewrite_history():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-006",
        memory=[MemoryReference(source_trace_ids=["WT006-TR-005"], memory_type="rollback_history")],
    )
    bundle.validate_visibility()
    assert bundle.memory[0].history_rewritten is False


def test_wt007_layers_coexist():
    bundle = RuntimeEvidenceBundle(
        walkthrough_id="WT-007",
        missingness=[MissingnessRecord(trace_id="WT007-TR-007", missingness_type="informational_absence")],
        contradictions=[ContradictionRecord(contradiction_id="WT007-CON-001", trace_ids=["a", "b"], contradiction_class="structural")],
        governance_reviews=[GovernanceReviewRecord(trace_ids=["WT007-TR-010", "WT007-TR-011"])],
        adaptations=[AdaptationRecord(parent_trace_ids=["WT007-TR-005"])],
        rollbacks=[RollbackRecord(parent_trace_ids=["WT007-TR-005"])],
        memory=[MemoryReference(source_trace_ids=["WT007-TR-006"], memory_type="recursive_governance")],
    )
    bundle.validate_combined_stress()
    assert len(bundle.layers_present()) == 6


if __name__ == "__main__":
    test_wt002_missingness_is_visible()
    test_wt003_competing_traces_coexist()
    test_wt004_governance_review_does_not_signoff()
    test_wt005_partial_adaptation_and_rollback_remain_open()
    test_wt006_memory_does_not_rewrite_history()
    test_wt007_layers_coexist()
    print("6 runtime-evidence checks passed")