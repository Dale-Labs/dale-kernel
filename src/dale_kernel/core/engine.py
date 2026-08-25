"""
DALE Kernel Main Engine — wires the WT-001 pipeline end-to-end.

Pipeline: Admissibility → Traceability → State Resolver → Event Store → Formal Result
"""
from typing import List, Tuple

from ..core.canons import (
    ObservationPackage,
    FormalDALEResult,
    FundamentalVariable,
)
from ..core.architecture import FormalInputPackage, FormalInputStatus
from ..services.admissibility import AdmissibilityEngine
from ..services.traceability import TraceabilityFactory
from ..services.state_resolver import StateResolver


class DALEKernel:
    """
    Main execution engine for the DALE Kernel.
    
    Currently implements WT-001 (Coherence Baseline).
    Future: WT-002 through WT-007.
    """

    def __init__(self, walkthrough_id: str = "WT-001"):
        self.walkthrough_id = walkthrough_id
        self.admissibility = AdmissibilityEngine()
        self.traceability = TraceabilityFactory()
        self.state_resolver = StateResolver(walkthrough_id)

    def execute(
        self,
        package: ObservationPackage,
        variables: List[FundamentalVariable],
        formal_input: FormalInputPackage | None = None,
    ) -> Tuple[FormalDALEResult, List[dict]]:
        """
        Execute the full WT-001 pipeline on one observation package.
        
        Returns:
            (formal_result, admissibility_errors)
            formal_result is None if admissibility fails.
        """
        # Step 1: Formal input closure gate
        if formal_input is not None:
            formal_input.close()
            if formal_input.status != FormalInputStatus.TRANSPARENT:
                return None, [{
                    "rule": "formal_input_closure",
                    "error": formal_input.status.value,
                    "details": [result.model_dump(mode="json") for result in formal_input.predicate_results if not result.passed],
                }]

        # Step 2: Admissibility check
        is_valid, errors = self.admissibility.validate_package(package)
        if not is_valid:
            return None, errors

        # Step 3: Create trace objects for each variable
        condition_id = (
            package.observation_condition.sector
            if hasattr(package.observation_condition, 'sector')
            else str(package.observation_condition)
        )
        root_trace = self.traceability.create_root_trace(
            condition_id=condition_id
        )
        trace_ids = [root_trace.trace_id]
        for v in variables:
            child_trace = self.traceability.create_child_trace(
                parent=root_trace,
                variable_ids=[v.variable_id],
            )
            self.traceability.link_variable_to_trace(v, child_trace)
            trace_ids.append(child_trace.trace_id)

        # Step 4: Execute state resolver (WT-001)
        result = self.state_resolver.execute_wt001(package, variables, trace_ids=trace_ids)

        return result, []

    @property
    def event_count(self) -> int:
        return self.state_resolver.events.event_count

    @property
    def current_state(self):
        return self.state_resolver.current_state