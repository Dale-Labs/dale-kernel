from typing import List, Optional, Dict, Any
from ..core.canons import TraceObject, TraceType, RuntimeState, FundamentalVariable
import uuid

class TraceabilityFactory:
    """
    Blueprint: The repository is memory infrastructure... Nothing is stored without traceability.
    Every runtime-relevant object must be trace-linked.
    """

    def create_root_trace(self, condition_id: str, markers: List[str] = []) -> TraceObject:
        """Create a root trace for a new observation cycle."""
        return TraceObject(
            trace_id=str(uuid.uuid4()),
            trace_type=TraceType.ROOT,
            condition_id=condition_id,
            runtime_state=RuntimeState.COHERENT,
            markers=markers
        )

    def create_child_trace(self, parent: TraceObject, variable_ids: List[str] = [], markers: List[str] = []) -> TraceObject:
        """Create a lineage-preserving child trace linked to specific variables."""
        return TraceObject(
            trace_id=str(uuid.uuid4()),
            trace_type=TraceType.PARENT_CHILD,
            parent_trace_id=parent.trace_id,
            linked_variable_ids=variable_ids,
            runtime_state=parent.runtime_state,
            markers=list(set(parent.markers + markers))
        )

    def link_variable_to_trace(self, variable: FundamentalVariable, trace: TraceObject):
        """
        Finalizes the link between an empirical variable and its trace lineage.
        Blueprint: Trace objects must include variable links where applicable.
        """
        if trace.trace_id not in variable.linked_trace_ids:
            variable.linked_trace_ids.append(trace.trace_id)
        
        if variable.variable_id not in trace.linked_variable_ids:
            trace.linked_variable_ids.append(variable.variable_id)

    def validate_lineage(self, trace_chain: List[TraceObject]) -> bool:
        """
        Ensures the chain of traces has no broken links.
        Blueprint: Implementation priority - Implement lineage validation.
        """
        for i in range(1, len(trace_chain)):
            current = trace_chain[i]
            previous = trace_chain[i-1]
            if current.parent_trace_id != previous.trace_id:
                return False
        return True
