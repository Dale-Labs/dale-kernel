"""Runtime evidence records for WT-002 through WT-007.

These records preserve instability and review state. They do not resolve
contradictions, governance fractures, adaptations, or historical conditions.
"""

from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceLayer(str, Enum):
    MISSINGNESS = "missingness"
    CONTRADICTION = "contradiction"
    GOVERNANCE_FRACTURE = "governance_fracture"
    ADAPTATION = "adaptation"
    ROLLBACK = "rollback"
    RECURSIVE_MEMORY = "recursive_memory"


class RuntimeEvidenceState(str, Enum):
    VISIBLE_UNRESOLVED = "visible_unresolved"
    PARTIAL_NOT_FINAL = "partial_not_final"
    CONDITIONAL_NOT_FINAL = "conditional_not_final"
    ROLLBACK_VISIBLE_NOT_CLOSED = "rollback_visible_not_closed"
    HISTORICAL_INFLUENCE_VISIBLE = "historical_influence_visible"


class MissingnessRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    missingness_type: str
    affected_variable_ids: List[str] = Field(default_factory=list)
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.VISIBLE_UNRESOLVED
    resolution_status: str = "unresolved"
    source_refs: List[str] = Field(default_factory=list)


class ContradictionRecord(BaseModel):
    contradiction_id: str
    trace_ids: List[str]
    affected_variable_ids: List[str] = Field(default_factory=list)
    contradiction_class: str
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.VISIBLE_UNRESOLVED
    resolution_status: str = "unresolved_visible"
    selected_trace_id: Optional[str] = None


class GovernanceReviewRecord(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_ids: List[str]
    review_questions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.VISIBLE_UNRESOLVED
    governance_resolution_generated: bool = False
    signoff_generated: bool = False


class AdaptationRecord(BaseModel):
    adaptation_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_trace_ids: List[str]
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.PARTIAL_NOT_FINAL
    resolution_status: str = "partial_not_final"
    unresolved_remainder_trace_ids: List[str] = Field(default_factory=list)
    full_coherence_claim_allowed: bool = False


class RollbackRecord(BaseModel):
    rollback_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_trace_ids: List[str]
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.ROLLBACK_VISIBLE_NOT_CLOSED
    rollback_suppressed: bool = False
    historical_state_refs: List[str] = Field(default_factory=list)


class MemoryReference(BaseModel):
    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    source_trace_ids: List[str]
    memory_type: str
    runtime_state: RuntimeEvidenceState = RuntimeEvidenceState.HISTORICAL_INFLUENCE_VISIBLE
    history_rewritten: bool = False


class RuntimeEvidenceBundle(BaseModel):
    """Layered WT evidence bundle with anti-collapse checks."""

    walkthrough_id: str
    trace_ids: List[str] = Field(default_factory=list)
    missingness: List[MissingnessRecord] = Field(default_factory=list)
    contradictions: List[ContradictionRecord] = Field(default_factory=list)
    governance_reviews: List[GovernanceReviewRecord] = Field(default_factory=list)
    adaptations: List[AdaptationRecord] = Field(default_factory=list)
    rollbacks: List[RollbackRecord] = Field(default_factory=list)
    memory: List[MemoryReference] = Field(default_factory=list)

    def validate_visibility(self) -> None:
        """Reject hidden collapse, suppression, overwrite, or false closure."""
        if any(record.selected_trace_id for record in self.contradictions):
            raise ValueError("contradiction traces cannot be selected automatically")
        if any(record.governance_resolution_generated for record in self.governance_reviews):
            raise ValueError("runtime evidence cannot generate final governance resolution")
        if any(record.signoff_generated for record in self.governance_reviews):
            raise ValueError("runtime evidence cannot generate signoff")
        if any(record.full_coherence_claim_allowed for record in self.adaptations):
            raise ValueError("partial adaptation cannot claim full coherence")
        if any(record.rollback_suppressed for record in self.rollbacks):
            raise ValueError("rollback visibility cannot be suppressed")
        if any(record.history_rewritten for record in self.memory):
            raise ValueError("recursive memory cannot rewrite history")

    def layers_present(self) -> set[EvidenceLayer]:
        layers = set()
        if self.missingness:
            layers.add(EvidenceLayer.MISSINGNESS)
        if self.contradictions:
            layers.add(EvidenceLayer.CONTRADICTION)
        if self.governance_reviews:
            layers.add(EvidenceLayer.GOVERNANCE_FRACTURE)
        if self.adaptations:
            layers.add(EvidenceLayer.ADAPTATION)
        if self.rollbacks:
            layers.add(EvidenceLayer.ROLLBACK)
        if self.memory:
            layers.add(EvidenceLayer.RECURSIVE_MEMORY)
        return layers

    def validate_combined_stress(self) -> None:
        """Ensure WT-007 layers coexist without being flattened."""
        self.validate_visibility()
        if len(self.layers_present()) < 2:
            raise ValueError("combined stress requires at least two visible evidence layers")