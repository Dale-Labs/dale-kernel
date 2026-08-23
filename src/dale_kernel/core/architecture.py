"""Project-to-ECOA boundary models.

These models preserve the distinction between source information, structural
declarations, bridge records, and the formal input package. They do not assign
ECOA or ARA values.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .canons import AbstractInput, ObservationCondition


class RepresentationMode(str, Enum):
    NATIVE_STRUCTURED = "native_structured"
    FORMAL = "formal"
    NARRATIVE = "narrative"
    ENVIRONMENTAL = "environmental"


class ArchitectureStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    REQUIRES_REVIEW = "requires_architecture_review"
    INSUFFICIENT = "architecture_insufficient"


class FormalInputStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    RELIABLE = "reliable_input"
    TRANSPARENT = "transparent_input"
    INSUFFICIENT = "insufficient_input"
    INADMISSIBLE = "inadmissible"
    REQUIRES_REVIEW = "requires_architecture_review"


class PredicateName(str, Enum):
    STRUCTURAL_ARCHITECTURE_CLOSED = "closed_structural_architecture"
    BRIDGE_CLOSED = "bridge_closed"
    INPUT_PACKAGE_CLOSED = "input_package_closed"
    TRACE_TRANSPARENT = "trace_transparent"


class PredicateResult(BaseModel):
    """Inspectable result of one formal-input closure predicate."""

    name: PredicateName
    passed: bool
    reason: str
    failed_requirements: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ProjectSource(BaseModel):
    """Versioned source object before structural declaration."""

    source_id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: str
    representation: RepresentationMode
    content: Dict[str, Any] = Field(default_factory=dict)
    source_ref: Optional[str] = None
    version: str = "1.0"


class StructuralDeclaration(BaseModel):
    """Declaration of how a source object participates in the project."""

    declaration_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    structural_class: str
    active_role: str
    systemhood: Optional[bool] = None
    representation_mode: RepresentationMode
    architecture_version: str
    status: ArchitectureStatus = ArchitectureStatus.OPEN
    failed_predicates: List[str] = Field(default_factory=list)
    declaration_ref: Optional[str] = None


class BridgeRecord(BaseModel):
    """Typed Project-to-ECOA bridge record."""

    bridge_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    declaration_id: str
    bridge_type: str
    mapping_ref: str
    bridge_version: str
    status: ArchitectureStatus = ArchitectureStatus.OPEN
    admitted_input_id: Optional[str] = None
    exclusions: List[str] = Field(default_factory=list)
    failed_predicates: List[str] = Field(default_factory=list)
    trace_refs: List[str] = Field(default_factory=list)


class ArchitectureReview(BaseModel):
    """Explicit review route for unresolved architecture."""

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    subject_id: str
    reason: str
    status: str = "open"
    source_id: Optional[str] = None
    declaration_id: Optional[str] = None
    bridge_id: Optional[str] = None


class FormalInputPackage(BaseModel):
    """Closed or pending package at the Project-to-ECOA boundary."""

    package_id: str = Field(default_factory=lambda: str(uuid4()))
    source: ProjectSource
    declaration: StructuralDeclaration
    bridge: BridgeRecord
    abstract_input: AbstractInput
    observation_condition: ObservationCondition
    adaptation_ref: str
    package_version: str = "1.0"
    status: FormalInputStatus = FormalInputStatus.OPEN
    architecture_review: Optional[ArchitectureReview] = None
    trace_path: List[str] = Field(default_factory=list)
    predicate_results: List[PredicateResult] = Field(default_factory=list)
    provenance_refs: Dict[str, str] = Field(default_factory=dict)

    @property
    def structural_architecture_closed(self) -> bool:
        return self.declaration.status == ArchitectureStatus.CLOSED

    @property
    def bridge_closed(self) -> bool:
        return self.bridge.status == ArchitectureStatus.CLOSED

    @property
    def input_package_closed(self) -> bool:
        return bool(self.abstract_input.content) and bool(self.observation_condition.sector)

    @property
    def reliable_input(self) -> bool:
        return (
            self.structural_architecture_closed
            and self.bridge_closed
            and self.input_package_closed
            and self.status in {FormalInputStatus.CLOSED, FormalInputStatus.RELIABLE, FormalInputStatus.TRANSPARENT}
        )

    @property
    def transparent_input(self) -> bool:
        return bool(self.trace_path) and bool(self.source.source_id) and bool(self.bridge.trace_refs)

    def evaluate_predicates(self) -> List[PredicateResult]:
        """Evaluate and retain boundary predicates without changing status."""
        results = [
            PredicateResult(
                name=PredicateName.STRUCTURAL_ARCHITECTURE_CLOSED,
                passed=self.structural_architecture_closed,
                reason="structural declaration is closed"
                if self.structural_architecture_closed
                else "structural declaration is not closed",
                failed_requirements=[] if self.structural_architecture_closed else ["declaration.status=CLOSED"],
                evidence_refs=[self.declaration.declaration_id],
            ),
            PredicateResult(
                name=PredicateName.BRIDGE_CLOSED,
                passed=self.bridge_closed,
                reason="Project-to-ECOA bridge is closed"
                if self.bridge_closed
                else "Project-to-ECOA bridge is not closed",
                failed_requirements=[] if self.bridge_closed else ["bridge.status=CLOSED"],
                evidence_refs=[self.bridge.bridge_id],
            ),
            PredicateResult(
                name=PredicateName.INPUT_PACKAGE_CLOSED,
                passed=self.input_package_closed,
                reason="formal input has content and observation condition"
                if self.input_package_closed
                else "formal input content or observation condition is incomplete",
                failed_requirements=[] if self.input_package_closed else ["abstract_input.content", "observation_condition.sector"],
                evidence_refs=[self.package_id, self.abstract_input.input_id],
            ),
            PredicateResult(
                name=PredicateName.TRACE_TRANSPARENT,
                passed=self.transparent_input,
                reason="source-to-bridge trace is present"
                if self.transparent_input
                else "source-to-bridge trace is incomplete",
                failed_requirements=[] if self.transparent_input else ["trace_path", "bridge.trace_refs"],
                evidence_refs=[self.source.source_id, *self.bridge.trace_refs],
            ),
        ]
        self.predicate_results = results
        return results

    def close(self) -> "FormalInputPackage":
        """Close only when declaration, bridge, package, and trace conditions hold."""
        self.provenance_refs = {
            "source_id": self.source.source_id,
            "declaration_id": self.declaration.declaration_id,
            "bridge_id": self.bridge.bridge_id,
            "package_id": self.package_id,
            "observation_condition": self.observation_condition.sector,
            "adaptation_ref": self.adaptation_ref,
        }
        self.evaluate_predicates()
        if not self.structural_architecture_closed:
            self.status = FormalInputStatus.REQUIRES_REVIEW
            self.architecture_review = ArchitectureReview(
                subject_id=self.source.source_id,
                reason="structural_declaration_not_closed",
                source_id=self.source.source_id,
                declaration_id=self.declaration.declaration_id,
            )
            return self
        if not self.bridge_closed:
            self.status = FormalInputStatus.REQUIRES_REVIEW
            self.architecture_review = ArchitectureReview(
                subject_id=self.source.source_id,
                reason="project_to_ecoa_bridge_not_closed",
                source_id=self.source.source_id,
                declaration_id=self.declaration.declaration_id,
                bridge_id=self.bridge.bridge_id,
            )
            return self
        if not self.input_package_closed:
            self.status = FormalInputStatus.INSUFFICIENT
            return self
        if not self.transparent_input:
            self.status = FormalInputStatus.REQUIRES_REVIEW
            return self
        self.status = FormalInputStatus.TRANSPARENT
        return self