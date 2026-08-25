from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
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
    COHERENT = "coherent"
    DEGRADED = "degraded"
    CONTRADICTION_VISIBLE = "contradiction_visible"
    GOVERNANCE_FRACTURED = "governance_fractured"
    ADAPTIVE_MIXED_STATE = "adaptive_mixed_state"
    MEMORY_VISIBLE = "memory_visible"
    COMBINED_STRESS_VISIBLE = "combined_stress_visible"

class TraceType(str, Enum):
    ROOT = "root"
    PARENT_CHILD = "parent_child"
    PAIRED_COMPETING = "paired_competing"
    MISSINGNESS_BEARING = "missingness_bearing"
    CONTRADICTION_BEARING = "contradiction_bearing"
    GOVERNANCE_FRACTURE = "governance_fracture"
    ADAPTIVE_RECONCILIATION = "adaptive_reconciliation"
    ROLLBACK_VISIBILITY = "rollback_visibility"
    RECURSIVE_MEMORY = "recursive_memory"
    COMBINED_STRESS = "combined_stress"

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

class VariableState(str, Enum):
    ASSIGNED = "assigned"        # Stage 1: ECOA Fixed
    NON_ASSIGNED = "non_assigned" # Stage 1: Unresolved
    RESOLVED = "resolved"         # Stage 2: ARA Resolved
    # Extended states from architectural review
    ECOA_FIXED = "ecoa_fixed"
    ARA_RESOLVED = "ara_resolved"
    STRUCTURALLY_INACTIVE = "structurally_inactive"
    INFORMATIONAL_ABSENCE = "informational_absence"


class ValueOrigin(str, Enum):
    """Origin of a formal value; no origin exists for inactive variables."""
    ECOA_ASSIGNED = "ecoa_assigned"
    ARA_COMPLETED = "ara_completed"

class FundamentalVariable(BaseModel):
    variable_id: str # v1 through v40
    variable_name: str
    value: Optional[float] = Field(None, ge=-1.0, le=1.0)
    state: VariableState
    linked_trace_ids: List[str] = []
    value_origin: Optional[ValueOrigin] = None
    
    @field_validator('variable_id')
    @classmethod
    def validate_v_range(cls, v: str) -> str:
        if not (v.startswith('v') and v[1:].isdigit() and 1 <= int(v[1:]) <= 40):
            raise ValueError("Variable ID must be between v1 and v40")
        return v
    
    @property
    def is_ecoa_fixed(self) -> bool:
        return self.state in (VariableState.ASSIGNED, VariableState.ECOA_FIXED)
    
    @property
    def is_non_assigned(self) -> bool:
        return self.state in (VariableState.NON_ASSIGNED,)
    
    @property
    def is_ara_resolved(self) -> bool:
        return self.state in (VariableState.RESOLVED, VariableState.ARA_RESOLVED)
    
    @property
    def is_inactive(self) -> bool:
        return self.state == VariableState.STRUCTURALLY_INACTIVE

# --- 4. OBSERVATION MODELS (Blueprint: Admissibility & Ingestion) ---

class AbstractInput(BaseModel):
    input_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_actor: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class ObservationPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    walkthrough_id: str
    scenario_type: str
    runtime_mode: str = "observation" # Always begins in observation
    inputs: List[AbstractInput]
    observation_condition: Union[Dict[str, str], 'ObservationCondition'] = Field(default_factory=dict)
    adaptation_ref: str = "default"
    version: str = "1.0"

# --- 5. OBSERVATION CONDITION (Blueprint: Engagement & Mode) ---

class EngagementType(str, Enum):
    LEVEL1_DIRECT = "level1_direct"
    LEVEL2_GUIDED = "level2_guided"
    LEVEL3_PLATFORM = "level3_platform"

class ObservationMode(str, Enum):
    PURE_OBSERVATION = "pure_observation"
    GUIDED = "guided"
    MIXED = "mixed"

class ObservationCondition(BaseModel):
    condition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scope: str = ""
    time: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    environment: str = ""
    purpose: str = ""
    formal_architecture_version: str = "1.0"
    sector: str
    geography: str = "default"
    engagement_type: EngagementType = EngagementType.LEVEL3_PLATFORM
    observation_mode: ObservationMode = ObservationMode.MIXED

# --- 6. STAGE OUTPUT MODELS (Blueprint: ECOA → ARA → Runner) ---

class ECOAOutput(BaseModel):
    observation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_id: str
    observation_condition: ObservationCondition
    adaptation_ref: str = "default"
    version: str = "1.0"
    fundamental_state: List[FundamentalVariable] = []
    assigned_variables: List[str] = []
    non_assigned_variables: List[str] = []
    trace_path: List[str] = []
    
    @property
    def has_non_assigned(self) -> bool:
        return len(self.non_assigned_variables) > 0

class ARAOutput(BaseModel):
    ara_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ecoa_observation_id: str
    ecoa_fixed_variables: List[FundamentalVariable] = []
    completion_field: List[str] = []
    completed_values: Dict[str, float] = {}
    solution_unique: bool = False
    solver_status: str = "not_executed"

class FormalDALEResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    result_revision: str = "1.0"
    ecoa_output: ECOAOutput
    ara_output: Optional[ARAOutput] = None
    trace_path: List[str] = []
    formal_status: str = "complete"
    technical_status: str = "complete"
    observation_id: Optional[str] = None
    package_id: Optional[str] = None
    package_revision: Optional[str] = None
    observation_condition_ref: Optional[str] = None
    formal_architecture_version: Optional[str] = None
    previous_result_id: Optional[str] = None
    validation_refs: List[str] = []
    application_view_refs: List[str] = []
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    
    @property
    def is_complete(self) -> bool:
        if self.ara_output is None:
            return not self.ecoa_output.has_non_assigned
        return self.ara_output.solver_status == "optimal"
    
    @property
    def variable_summary(self) -> Dict[str, int]:
        ecoa_fixed = len(self.ecoa_output.assigned_variables)
        ara_resolved = len(self.ara_output.completed_values) if self.ara_output else 0
        non_assigned = len(self.ecoa_output.non_assigned_variables) - ara_resolved
        return {
            "ecoa_fixed": ecoa_fixed,
            "ara_resolved": ara_resolved,
            "non_assigned": non_assigned,
        }
