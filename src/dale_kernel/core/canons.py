from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# --- 1. ENUMS (Blueprint: State Machine & Semantic States) ---

class AdmissibilityError(Exception):
    def __init__(self, condition_id: int, message: str):
        self.condition_id = condition_id
        self.message = message
        super().__init__(f"Admissibility Violation (Rule {condition_id}): {message}")


class RuntimeState(str, Enum):
    """Walkthrough-level runtime states (WT-001 through WT-007)."""
    COHERENT = "coherent"
    DEGRADED = "degraded"
    CONTRADICTION_VISIBLE = "contradiction_visible"
    GOVERNANCE_FRACTURED = "governance_fractured"
    ADAPTIVE_MIXED_STATE = "adaptive_mixed_state"
    MEMORY_VISIBLE = "memory_visible"
    COMBINED_STRESS_VISIBLE = "combined_stress_visible"


class VariableState(str, Enum):
    """
    Canonical variable assignment states per Boris §6-7 and Jielekeze §5.3-5.4.
    
    ECOA_FIXED:     Assigned during Stage 1 observation. Immutable thereafter.
                    Belongs to V_fix. Must not be reopened by ARA.
    NON_ASSIGNED:   Remains unresolved after completed ECOA observation.
                    Belongs to V_na. Enters ARA completion field U when Stage 2 is admissible.
    ARA_RESOLVED:   Completed by Stage 2 ARA minimization.
                    Must remain distinguishable from ECOA_FIXED in all outputs.
    STRUCTURALLY_INACTIVE: Variable not active under current observation condition.
    INFORMATIONAL_ABSENCE: Source information exists but is unavailable.
                           Explicitly NOT zero (informational absence ≠ 0).
    STRUCTURAL_ABSENCE: Variable not applicable to this observation.
    """
    ECOA_FIXED = "ecoa_fixed"
    NON_ASSIGNED = "non_assigned"
    ARA_RESOLVED = "ara_resolved"
    STRUCTURALLY_INACTIVE = "structurally_inactive"
    INFORMATIONAL_ABSENCE = "informational_absence"
    STRUCTURAL_ABSENCE = "structural_absence"

    # Backward compatibility aliases
    ASSIGNED = "ecoa_fixed"       # deprecated — use ECOA_FIXED
    RESOLVED = "ara_resolved"     # deprecated — use ARA_RESOLVED


class TraceType(str, Enum):
    """Trace object types covering the full DALE pipeline (Boris §15)."""
    # Pipeline stage traces
    INPUT_FORMATION = "input_formation"       # F_in: source → formed input
    ECOA_OBSERVATION = "ecoa_observation"     # Stage 1 observation execution
    ARA_COMPLETION = "ara_completion"         # Stage 2 completion execution
    
    # Structural trace types
    ROOT = "root"
    PARENT_CHILD = "parent_child"
    
    # Instability-bearing traces (WT-002 through WT-007)
    PAIRED_COMPETING = "paired_competing"
    MISSINGNESS_BEARING = "missingness_bearing"
    CONTRADICTION_BEARING = "contradiction_bearing"
    GOVERNANCE_FRACTURE = "governance_fracture"
    ADAPTIVE_RECONCILIATION = "adaptive_reconciliation"
    ROLLBACK_VISIBILITY = "rollback_visibility"
    RECURSIVE_MEMORY = "recursive_memory"
    COMBINED_STRESS = "combined_stress"


class ObservationMode(str, Enum):
    """How the observation was conducted (Jielekeze §5.2, CoS schema)."""
    FACILITATED_SESSION = "facilitated_session"
    DOCUMENT_REVIEW = "document_review"
    INTERVIEW_SERIES = "interview_series"
    MIXED = "mixed"
    SELF_REPORTED = "self_reported"
    AI_ASSISTED = "ai_assisted"


class EngagementType(str, Enum):
    """Engagement level for the observation (CoS schema)."""
    LEVEL1_CLIENT_PROJECT = "Level1_ClientProject"
    LEVEL2_COMMUNITY_SPRINT = "Level2_CommunitySprint"
    LEVEL3_PLATFORM = "Level3_Platform"

# --- 2. CORE TRACE COMPONENTS (Blueprint: Traceability First) ---

class TraceObject(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_type: TraceType
    condition_id: Optional[str] = None
    parent_trace_id: Optional[str] = None
    linked_variable_ids: List[str] = []
    runtime_state: RuntimeState
    lineage_status: str = "active"
    observability_status: str = "visible"
    markers: List[str] = [] # missingness, contradiction, etc.
    
    # Anti-collapse control checkpoints
    suppression_prevented: bool = True
    overwrite_prevented: bool = True
    normalization_prevented: bool = True

# --- 3. VARIABLE REGISTRY (Blueprint: v1-v40 Fundamental Variables) ---

class FundamentalVariable(BaseModel):
    """
    One of the 40 canonical fundamental variables (v1-v40).
    
    Per Boris §6: each activated fundamental variable must preserve either
    an assigned value in [-1, 1] or an explicit status showing why a value
    is not available. Informational absence ≠ 0.
    """
    variable_id: str  # v1 through v40
    variable_name: str
    value: Optional[float] = Field(None, ge=-1.0, le=1.0)
    state: VariableState
    linked_trace_ids: List[str] = []
    layer: str = "fundamental"  # fundamental | operational
    
    @field_validator('variable_id')
    @classmethod
    def validate_v_range(cls, v: str) -> str:
        if not (v.startswith('v') and v[1:].isdigit() and 1 <= int(v[1:]) <= 40):
            raise ValueError("Variable ID must be between v1 and v40")
        return v
    
    @property
    def is_ecoa_fixed(self) -> bool:
        return self.state == VariableState.ECOA_FIXED
    
    @property
    def is_non_assigned(self) -> bool:
        return self.state == VariableState.NON_ASSIGNED
    
    @property
    def is_ara_resolved(self) -> bool:
        return self.state == VariableState.ARA_RESOLVED
    
    @property
    def is_inactive(self) -> bool:
        return self.state in (VariableState.STRUCTURALLY_INACTIVE, VariableState.STRUCTURAL_ABSENCE)


# --- 4. OBSERVATION CONDITION (Boris §4, Jielekeze §5.2) ---

class ObservationCondition(BaseModel):
    """
    The declared condition c under which one ECOA observation executes.
    
    Per Boris §4: one ECOA observation = one execution of the fixed architecture
    on one finite submitted package under one admissible observation condition.
    """
    condition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sector: str = ""               # e.g. climate finance, health, education, livelihoods
    geography: str = ""            # e.g. Mathare, Maono, Kisumu
    engagement_type: EngagementType = EngagementType.LEVEL3_PLATFORM
    observation_mode: ObservationMode = ObservationMode.MIXED
    date: Optional[str] = None     # ISO date
    notes: str = ""
    
    @property
    def label(self) -> str:
        """Human-readable condition label."""
        return f"{self.sector}/{self.geography}/{self.engagement_type.value}"


# --- 5. SOURCE INFORMATION (Boris §3, Jielekeze §5.1) ---

class SourceInformation(BaseModel):
    """
    Raw information before input formation.
    
    D_source = D_user ∪ D_external  (Boris eq. 4)
    
    This is NOT an admissible ECOA input. It must pass through F_in first.
    """
    source_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_information: Dict[str, Any] = {}     # D_user: goals, constraints, aspirations, etc.
    external_information: Dict[str, Any] = {}  # D_external: partner data, public datasets, etc.
    source_actor: str = ""                     # Who provided this information
    timestamp: datetime = Field(default_factory=datetime.now)
    previous_observation_id: Optional[str] = None  # Link to prior formal result, if any


# --- 6. ABSTRACT INPUT (Admissibility & Ingestion) ---

class AbstractInput(BaseModel):
    """
    One admissible abstract input unit formed by F_in.
    
    Per Boris §3: must be expressible as a system under the fixed DALE
    principle-model frame. Every active internal unit must be realizable
    as an operational or fundamental variable.
    """
    input_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_actor: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    source_refs: List[str] = []  # Trace back to SourceInformation.source_id
    admissibility_status: str = "pending"  # pending | admissible | form_noise | decomposition_noise | architectural_noise


# --- 7. OBSERVATION PACKAGE (Boris §4) ---

class ObservationPackage(BaseModel):
    """
    One admissible observation package submitted to ECOA.
    
    Per Boris eq. 6: O(1) = Observe(A(1)_adm,c | B(1)_DALE)
    
    The package is atomic — one execution, one condition, one set of inputs.
    A partial application session is NOT an ObservationPackage.
    """
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    walkthrough_id: str = "WT-001"
    scenario_type: str = "Baseline"
    runtime_mode: str = "observation"  # Always begins in observation
    inputs: List[AbstractInput]
    observation_condition: ObservationCondition
    adaptation_ref: str = ""           # Active DALE-grounded ECOA adaptation reference
    version: str = "1.0"
    source_trace: List[str] = []       # Chain of source_information.source_id values
    timestamp: datetime = Field(default_factory=datetime.now)


# --- 8. ECOA STAGE 1 OUTPUT (Boris §5-6) ---

class ECOAOutput(BaseModel):
    """
    Layered Stage 1 observational output.
    
    Per Boris eq. 8: A(1)_adm → S(1)_in → R(1)_term → E(1)_fund → E(1)_op → E(1)_a
    
    ECOA does NOT produce programmes, communities, groups, activities,
    labs, recommendations, or dashboard instructions.
    """
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str                                    # Reference to ObservationPackage
    observation_condition: ObservationCondition
    adaptation_ref: str = ""
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Layered empirical states
    fundamental_state: List[FundamentalVariable] = []  # E(1)_fund
    operational_state: Dict[str, Any] = {}             # E(1)_op
    family_states: Dict[str, Any] = {}                 # Family-level empirical states
    abstract_state: Dict[str, Any] = {}                # E(1)_a — abstract-level return
    
    # Partition (Boris eq. 16)
    assigned_variables: List[str] = []    # V_fix — variable IDs assigned by ECOA
    non_assigned_variables: List[str] = [] # V_na — variable IDs remaining unresolved
    
    # Statuses (Boris §6 — must remain distinguishable)
    informational_absences: List[str] = []  # Variable IDs with informational absence
    structural_absences: List[str] = []     # Variable IDs with structural absence
    structural_insufficiencies: List[str] = []  # Variable IDs with structural insufficiency
    
    # Traceability
    trace_path: List[str] = []  # Ordered trace: source → formed input → observation → ...
    used_principles: List[str] = []
    used_models: List[str] = []
    
    @property
    def has_non_assigned(self) -> bool:
        """True if ARA Stage 2 may be required (V_na ≠ ∅)."""
        return len(self.non_assigned_variables) > 0
    
    @property
    def is_ara_admissible(self) -> bool:
        """
        Stage 2 transition τ_{1→2} is admissible only when:
        1. ECOA observation is complete (this object exists)
        2. V_na is non-empty
        3. Inherited condition is sufficient for Stage 2 coordination
        """
        return self.has_non_assigned


# --- 9. ARA STAGE 2 OUTPUT (Boris §7) ---

class ARAOutput(BaseModel):
    """
    Stage 2 completion output.
    
    Per Boris eq. 20-26: ARA solves the constrained quadratic minimization
    J(x) = Σ(x_i - a_i)² + Φ_arch(x) + Φ_recon(x) over Ω ⊆ [-1,1]^m.
    
    The solution must be unique (∃! x* ∈ Ω).
    ARA_RESOLVED values must remain distinguishable from ECOA_FIXED values.
    """
    completion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ecoa_observation_id: str                        # Reference to ECOAOutput
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    
    # Inherited from ECOA (immutable)
    ecoa_fixed_variables: List[FundamentalVariable] = []  # V_fix — never modified
    
    # Completion field
    completion_field: List[str] = []       # U = V_na — variable IDs entering completion
    anchor_mode: str = "zero-anchor"       # zero-anchor | family-anchor
    completed_values: Dict[str, float] = {} # E_comp = {(u_i, x*_i)}
    
    # Readable reconstruction (Boris eq. 25)
    readable_config: Dict[str, Any] = {}   # E(2)_read = R(x*) = Ax* + b
    
    # Solution metadata
    solution_unique: bool = True           # Must be True (∃! x*)
    objective_value: Optional[float] = None  # J(x*)
    iterations: int = 0
    solver_status: str = "pending"
    
    # Traceability
    trace_path: List[str] = []
    
    @property
    def all_variables(self) -> List[FundamentalVariable]:
        """Combined ECOA-fixed + ARA-resolved variables."""
        result = list(self.ecoa_fixed_variables)
        for var_id, value in self.completed_values.items():
            result.append(FundamentalVariable(
                variable_id=var_id,
                variable_name=var_id,  # Name resolved from registry
                value=value,
                state=VariableState.ARA_RESOLVED
            ))
        return result


# --- 10. FORMAL DALE RESULT (Boris §11, Jielekeze §5.5) ---

class FormalDALEResult(BaseModel):
    """
    Authoritative formal result combining ECOA + ARA outputs.
    
    Per Jielekeze §5.5: every observation must produce ONE authoritative
    formal result. The dashboard is a VIEW of this result, not a replacement.
    
    Per Boris §11: the formal return must distinguish ECOA-assigned from
    ARA-resolved, and preserve all structural statuses.
    """
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ecoa_output: ECOAOutput
    ara_output: Optional[ARAOutput] = None  # None if Stage 2 was not required/admissible
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    
    # Observation history (Boris §14)
    previous_result_id: Optional[str] = None
    change_trigger: str = ""  # What changed to produce this new observation
    
    # Full traceability (Boris §15)
    trace_path: List[str] = []  # Complete ordered trace source → ... → formal result
    
    @property
    def is_complete(self) -> bool:
        """True if no non-assigned variables remain unresolved."""
        if self.ecoa_output.has_non_assigned and self.ara_output is None:
            return False
        return True
    
    @property
    def variable_summary(self) -> Dict[str, int]:
        """Count of variables by state."""
        counts = {s.value: 0 for s in VariableState}
        for v in self.ecoa_output.fundamental_state:
            counts[v.state.value] = counts.get(v.state.value, 0) + 1
        if self.ara_output:
            counts[VariableState.ARA_RESOLVED.value] = len(self.ara_output.completed_values)
        return counts
