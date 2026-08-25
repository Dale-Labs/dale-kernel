"""
State Resolver — manages walkthrough state transitions (WT-001 through WT-007).

Per the DALE Runtime Canon v1: each walkthrough defines a canonical runtime role.
WT-001 is the coherence baseline — the minimum executable structure for trace
registration, variable linkage, observation intake, and closure.
"""
from typing import List

from ..core.canons import (
    RuntimeState,
    ObservationPackage,
    ECOAOutput,
    FormalDALEResult,
    FundamentalVariable,
    VariableState,
    ValueOrigin,
)
from .event_store import EventStore, EventType


class StateResolver:
    """
    Manages the seven-layer state machine (WT-001 through WT-007).
    
    WT-001 (Coherence Baseline):
    - All 40 variables observed and assigned
    - No missingness, contradiction, or governance fracture
    - Produces a clean ECOA output with V_na = ∅
    - No ARA required (completion field is empty)
    """

    def __init__(self, walkthrough_id: str = "WT-001"):
        self.walkthrough_id = walkthrough_id
        self.current_state = RuntimeState.COHERENT
        self.events = EventStore(walkthrough_id)

    # ── WT-001: Coherence Baseline ──────────────────────────────────

    def execute_wt001(
        self,
        package: ObservationPackage,
        variables: List[FundamentalVariable],
        trace_ids: List[str] | None = None,
    ) -> FormalDALEResult:
        """
        Execute WT-001 coherent baseline observation.
        
        WT-001 assumes all variables are assigned with no instability.
        Produces an ECOA output with empty V_na (no ARA needed).
        """
        self.events.append(EventType.OBSERVATION_STARTED, {
            "package_id": package.package_id,
            "walkthrough_id": self.walkthrough_id,
            "variable_count": len(variables),
        })

        # Classify variables into V_fix and V_na
        assigned = []
        non_assigned = []
        for v in variables:
            if v.is_ecoa_fixed:
                v.value_origin = ValueOrigin.ECOA_ASSIGNED
                assigned.append(v.variable_id)
                self.events.append(EventType.VARIABLE_ASSIGNED, {
                    "variable_id": v.variable_id,
                    "variable_name": v.variable_name,
                    "value": v.value,
                })
            elif v.is_non_assigned:
                non_assigned.append(v.variable_id)
                self.events.append(EventType.VARIABLE_NON_ASSIGNED, {
                    "variable_id": v.variable_id,
                    "variable_name": v.variable_name,
                    "reason": "unresolved after observation",
                })

        # Build ECOA output
        ecoa = ECOAOutput(
            package_id=package.package_id,
            observation_condition=package.observation_condition,
            adaptation_ref=package.adaptation_ref,
            version=package.version,
            fundamental_state=variables,
            assigned_variables=assigned,
            non_assigned_variables=non_assigned,
            trace_path=[f"package:{package.package_id}"],
        )

        self.events.append(EventType.ECOA_COMPLETED, {
            "observation_id": ecoa.observation_id,
            "assigned_count": len(assigned),
            "non_assigned_count": len(non_assigned),
        })

        # WT-001: no ARA needed (V_na should be empty for coherent baseline)
        if ecoa.has_non_assigned:
            self.current_state = RuntimeState.DEGRADED
            self.events.append(EventType.ERROR, {
                "message": "WT-001 expected coherent baseline but found non-assigned variables",
                "non_assigned": non_assigned,
            })
        else:
            self.current_state = RuntimeState.COHERENT

        # Build formal result with full trace lineage
        # Per Architectural Review: expose complete source-to-result trace
        trace_lineage = [
            f"walkthrough:{self.walkthrough_id}",
            f"package:{package.package_id}",
            f"observation:{ecoa.observation_id}",
        ]
        if trace_ids:
            trace_lineage.extend(f"trace:{trace_id}" for trace_id in trace_ids)
        # Add source information traces from inputs
        for inp in package.inputs:
            trace_lineage.insert(0, f"source:{inp.source_actor}")
            if "_source_session" in inp.content:
                trace_lineage.insert(0, f"session:{inp.content['_source_session']}")
        
        result = FormalDALEResult(
            ecoa_output=ecoa,
            ara_output=None,
            trace_path=trace_lineage,
            observation_id=ecoa.observation_id,
            package_id=package.package_id,
            package_revision=package.version,
            observation_condition_ref=ecoa.observation_condition.condition_id,
            formal_architecture_version=package.adaptation_ref,
        )

        self.events.append(EventType.RESULT_PRODUCED, {
            "result_id": result.result_id,
            "is_complete": result.is_complete,
            "variable_summary": result.variable_summary,
        })

        return result

    # ── State transition ────────────────────────────────────────────

    def transition_to(self, new_state: RuntimeState, reason: str = ""):
        """Record a state transition with reason."""
        old = self.current_state
        self.current_state = new_state
        self.events.append(EventType.STATE_TRANSITION, {
            "from": old.value,
            "to": new_state.value,
            "reason": reason,
        })

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def make_coherent_variables(count: int = 40) -> List[FundamentalVariable]:
        """
        Create a set of coherent variables for WT-001 baseline testing.
        All variables are ECOA_FIXED with neutral values.
        """
        names = [
            "identity", "dignity", "agency", "psychological_safety",
            "participant_readiness", "participant_overload", "participant_freeze",
            "reflective_capacity", "adaptive_thinking", "pattern_noticing",
            "cognitive_load", "beneficiary_position", "customer_position",
            "payer_position", "payment_capacity", "decision_authority",
            "community_participation", "community_stewardship",
            "system_structure", "decision_pathway", "power_asymmetry",
            "invisible_influence", "localization", "local_actor_agency",
            "local_actor_autonomy", "contextual_fit", "value", "impact",
            "resourcing", "money_flow", "impact_flow", "data_flow",
            "decision_flow", "flow_coherence", "root_cause_depth",
            "problem_priority", "assumption_exposure", "learning_adaptivity",
            "continuity_risk", "roadmap_readiness",
        ]
        variables = []
        for i, name in enumerate(names[:count], start=1):
            variables.append(FundamentalVariable(
                variable_id=f"v{i}",
                variable_name=name,
                value=0.0,
                state=VariableState.ECOA_FIXED,
            ))
        return variables