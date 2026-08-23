"""
Input Formation Service — bridges raw source information to ECOA-admissible packages.

Per the Architectural Review (2026-07-27):
- Sits BEFORE formal ECOA observation
- Structures natural-language source information into FormedInput
- Exposes ambiguity, preserves incompleteness, maintains source references
- NEVER invents empirical values, assigns ECOA_FIXED states, or bypasses admissibility

Per ARA-NR (Boris Dzhongov, 2026):
- Treats source information as an active permutation field
- Distinguishes admissible expansion from unnecessary over-extension
- Returns Status outputs when the field cannot be validly reduced
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field

from ..core.canons import (
    AbstractInput,
    ObservationCondition,
    ObservationPackage,
    TraceObject,
    TraceType,
    RuntimeState,
)


class FormationStatus(str, Enum):
    """Status of the input formation attempt."""
    FORMED = "formed"                       # Successfully structured
    INSUFFICIENT_INFORMATION = "insufficient_information"  # Missing required fields
    AMBIGUITY_PRESERVED = "ambiguity_preserved"  # Multiple interpretations, none resolved
    OVER_SPECIFIED = "over_specified"       # Too much information, risk of noise
    INVALID = "invalid"                     # Cannot be formed under any interpretation


class FormedInput(BaseModel):
    """
    A structured, traceable input candidate produced from raw source information.
    
    This is NOT yet an ObservationPackage. It must still pass Admissibility checks.
    """
    input_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_session_id: str
    source_user_id: str
    environment: str = "jielekeze"
    
    # The structured content derived from raw source
    goal: Optional[str] = None
    blockers: List[str] = []
    aspiration_text: Optional[str] = None
    county: Optional[str] = None
    ward: Optional[str] = None
    age_range: Optional[str] = None
    work_type: Optional[str] = None
    
    # Formation metadata
    formation_status: FormationStatus
    unresolved_ambiguities: List[str] = []   # Things we couldn't resolve
    missing_required_fields: List[str] = []  # Fields that were absent
    source_trace: List[str] = []             # Trace back to raw source
    formation_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Guardrail evidence
    no_invented_values: bool = True
    explicit_ambiguity_preserved: bool = True
    source_to_abstraction_trace: bool = True


class InputFormationService:
    """
    Middleware that transforms raw AssessmentResponses into FormedInput candidates.
    
    Design principles (from Architectural Review):
    1. Never invent values — if a field is absent, mark it missing, don't guess
    2. Preserve ambiguity — if multiple interpretations exist, expose all of them
    3. Maintain source trace — every formed field must link back to raw source
    4. Admissibility gate — output must be validatable by AdmissibilityEngine
    
    ARA-NR alignment:
    - Raw source = the initial active permutation field P_0
    - FormedInput = a reduced field after one reduction step
    - Status outputs = when the field cannot be validly reduced
    """
    
    # Required fields for a minimally admissible input
    REQUIRED_FIELDS = {"goal", "county", "ward"}
    
    # Fields that must never be invented — if absent, they're absent
    NO_INVENT_FIELDS = {"goal", "aspiration_text", "age_range", "work_type"}
    
    def form_input(
        self,
        session_id: str,
        user_id: str,
        source: Dict[str, Any],
        environment: str = "jielekeze",
    ) -> Tuple[FormedInput, List[TraceObject]]:
        """
        Transform raw AssessmentResponses into a FormedInput candidate.
        
        Args:
            session_id: The Check My Hustle session ID
            user_id: The authenticated user ID
            source: Raw AssessmentResponses dict from the API
            environment: jielekeze, ape, or sve
            
        Returns:
            Tuple of (FormedInput, list of TraceObjects documenting the formation)
        """
        traces: List[TraceObject] = []
        
        # Create root trace for this formation attempt
        root_trace = TraceObject(
            trace_type=TraceType.ROOT,
            condition_id=f"session:{session_id}",
            runtime_state=RuntimeState.COHERENT,
            markers=["input_formation", environment],
        )
        traces.append(root_trace)
        
        # Extract fields with strict no-invention policy
        goal = self._safe_extract(source, "goal")
        blockers = self._safe_extract_list(source, "blockers")
        aspiration = self._safe_extract(source, "aspiration_text")
        county = self._safe_extract(source, "county")
        ward = self._safe_extract(source, "ward")
        age_range = self._safe_extract(source, "age_range")
        work_type = self._safe_extract(source, "work_type")
        
        # Build source trace
        source_trace = [
            f"session:{session_id}",
            f"user:{user_id}",
            f"environment:{environment}",
        ]
        
        # Check for missing required fields
        missing = self._check_required(
            goal=goal, county=county, ward=ward
        )
        
        # Check for unresolvable ambiguities
        ambiguities = self._detect_ambiguities(
            goal=goal,
            blockers=blockers,
            aspiration=aspiration,
        )
        
        # Determine formation status
        if missing:
            status = FormationStatus.INSUFFICIENT_INFORMATION
            child_trace = TraceObject(
                trace_type=TraceType.MISSINGNESS_BEARING,
                parent_trace_id=root_trace.trace_id,
                runtime_state=RuntimeState.DEGRADED,
                markers=["missing_required", *missing],
            )
            traces.append(child_trace)
        elif ambiguities:
            status = FormationStatus.AMBIGUITY_PRESERVED
            child_trace = TraceObject(
                trace_type=TraceType.CONTRADICTION_BEARING,
                parent_trace_id=root_trace.trace_id,
                runtime_state=RuntimeState.CONTRADICTION_VISIBLE,
                markers=["ambiguity_preserved", *ambiguities],
            )
            traces.append(child_trace)
        else:
            status = FormationStatus.FORMED
            child_trace = TraceObject(
                trace_type=TraceType.PARENT_CHILD,
                parent_trace_id=root_trace.trace_id,
                runtime_state=RuntimeState.COHERENT,
                markers=["formed_successfully"],
            )
            traces.append(child_trace)
        
        formed = FormedInput(
            source_session_id=session_id,
            source_user_id=user_id,
            environment=environment,
            goal=goal,
            blockers=blockers,
            aspiration_text=aspiration,
            county=county,
            ward=ward,
            age_range=age_range,
            work_type=work_type,
            formation_status=status,
            unresolved_ambiguities=ambiguities,
            missing_required_fields=missing,
            source_trace=source_trace,
            no_invented_values=True,
            explicit_ambiguity_preserved=len(ambiguities) == 0 or status == FormationStatus.AMBIGUITY_PRESERVED,
            source_to_abstraction_trace=True,
        )
        
        return formed, traces
    
    def to_abstract_input(self, formed: FormedInput) -> AbstractInput:
        """
        Convert a FormedInput into an AbstractInput suitable for AdmissibilityEngine.
        
        This is the bridge between input formation and formal ECOA observation.
        The AbstractInput preserves all formation metadata in its content dict.
        """
        return AbstractInput(
            source_actor=f"user:{formed.source_user_id}",
            content={
                "arch_frame": "P1",  # Default principle frame — may be overridden
                "goal": formed.goal,
                "blockers": formed.blockers,
                "aspiration_text": formed.aspiration_text,
                "county": formed.county,
                "ward": formed.ward,
                "age_range": formed.age_range,
                "work_type": formed.work_type,
                # Formation metadata for traceability
                "_formation_status": formed.formation_status.value,
                "_unresolved_ambiguities": formed.unresolved_ambiguities,
                "_missing_fields": formed.missing_required_fields,
                "_source_session": formed.source_session_id,
                "_input_id": formed.input_id,
            },
        )
    
    def to_observation_package(
        self,
        formed: FormedInput,
        walkthrough_id: str = "WT-001",
    ) -> ObservationPackage:
        """
        Convert a FormedInput into an ObservationPackage ready for ECOA.
        
        This is the final step before formal observation begins.
        """
        abstract_input = self.to_abstract_input(formed)
        
        return ObservationPackage(
            walkthrough_id=walkthrough_id,
            scenario_type=formed.environment,
            inputs=[abstract_input],
            observation_condition=ObservationCondition(
                sector=formed.environment,
                geography=f"{formed.county or 'unknown'}/{formed.ward or 'unknown'}",
            ),
        )
    
    # ── Private helpers ─────────────────────────────────────────────
    
    def _safe_extract(self, source: Dict[str, Any], field: str) -> Optional[str]:
        """
        Extract a field without inventing a value.
        
        Guardrail: If the field is absent, return None.
        If the field is present but empty, return None.
        Never substitute a default or inferred value.
        """
        value = source.get(field)
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return str(value)
    
    def _safe_extract_list(self, source: Dict[str, Any], field: str) -> List[str]:
        """
        Extract a list field safely.
        """
        value = source.get(field)
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
    
    def _check_required(
        self, goal: Optional[str], county: Optional[str], ward: Optional[str]
    ) -> List[str]:
        """Check which required fields are missing."""
        missing = []
        if not goal:
            missing.append("goal")
        if not county:
            missing.append("county")
        if not ward:
            missing.append("ward")
        return missing
    
    def _detect_ambiguities(
        self,
        goal: Optional[str],
        blockers: List[str],
        aspiration: Optional[str],
    ) -> List[str]:
        """
        Detect unresolvable ambiguities in the formed input.
        
        Examples:
        - Goal contradicts blockers (e.g., "start business" but "no capital" with no resolution path)
        - Aspiration is internally contradictory
        - Multiple incompatible interpretations possible
        
        This is a lightweight check — full ARA-NR would do deeper permutation analysis.
        """
        ambiguities = []
        
        # Check for contradictory goal-blocker combinations
        if goal and blockers:
            goal_lower = goal.lower()
            blocker_text = " ".join(blockers).lower()
            
            # If goal mentions starting/growing but blockers mention no capital/resources
            if any(word in goal_lower for word in ["start", "grow", "expand", "build"]):
                if any(word in blocker_text for word in ["capital", "money", "fund", "resource", "finance"]):
                    ambiguities.append("goal_requires_resources_but_blockers_indicate_lack")
        
        # Check for overly vague goals that could mean many things
        if goal and len(goal.split()) < 3:
            ambiguities.append("goal_too_vague_for_reliable_interpretation")
        
        # Check for aspiration that contradicts goal
        if goal and aspiration:
            if goal.lower() in aspiration.lower() and len(aspiration.split()) <= len(goal.split()) + 2:
                ambiguities.append("aspiration_may_be_restating_goal_rather_than_extending")
        
        return ambiguities