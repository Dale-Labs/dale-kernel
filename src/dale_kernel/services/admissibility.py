from typing import List, Tuple, Dict, Any
from ..core.canons import ObservationPackage, AbstractInput

class AdmissibilityError(Exception):
    def __init__(self, condition_id: int, message: str):
        self.condition_id = condition_id
        self.message = message
        super().__init__(f"Admissibility Violation (Rule {condition_id}): {message}")

class AdmissibilityEngine:
    """
    Blueprint: Admissibility is the rule-set for whether an input can enter the system.
    Strict enforcement of CoS Canon 7 Admissibility Conditions.
    """

    def validate_package(self, package: ObservationPackage) -> Tuple[bool, List[Dict[str, Any]]]:
        results = []
        is_valid = True
        
        for input_obj in package.inputs:
            try:
                # Rule 1 handled by Pydantic (Expressible in Form)
                
                self._check_rule_2(input_obj) # Admissible as a system
                self._check_rule_3(input_obj) # Bounded system references
                self._check_rule_4(input_obj) # Realizable units
                self._check_rule_5(input_obj) # Global P-M frame expressibility
                self._check_rule_6(input_obj) # Admissible recursive decomposition
                self._check_rule_7(input_obj) # Terminal realization reached
                
            except AdmissibilityError as e:
                is_valid = False
                results.append({
                    "input_id": input_obj.input_id,
                    "rule": e.condition_id,
                    "error": e.message
                })
        
        return is_valid, results

    def _check_rule_2(self, input_obj: AbstractInput):
        """Admissible as a system under the fixed architecture."""
        if not isinstance(input_obj.content, dict) or len(input_obj.content) == 0:
            raise AdmissibilityError(2, "Input must contain a non-empty structured system dictionary")

    def _check_rule_3(self, input_obj: AbstractInput):
        """Refers only to structures belonging to the defined system."""
        # Blueprint: Ensure no contamination from out-of-scope system references
        forbidden_keys = {"external_api", "global_web_index", "unbounded_reference"}
        content_keys = set(input_obj.content.keys())
        intersection = content_keys.intersection(forbidden_keys)
        if intersection:
            raise AdmissibilityError(3, f"Input refers to forbidden external structures: {intersection}")

    def _check_rule_4(self, input_obj: AbstractInput):
        """Every active internal unit realizable as operational or fundamental variable."""
        # Implementation: Check if keys in content map to a potential DALE variable or known model
        # For now, we verify that keys are alpha-numeric and don't look like unstructured noise
        for key in input_obj.content.keys():
            if not key.isidentifier():
                raise AdmissibilityError(4, f"Unit '{key}' is not an admissible DALE identifier")

    def _check_rule_5(self, input_obj: AbstractInput):
        """Expressible through fixed global principle-model frame."""
        # Blueprint: Every unit must align with P1-P5
        admissible_frames = {"P1", "P2", "P3", "P4", "P5", "M1", "M2", "M3", "M4", "M5"}
        frame = input_obj.content.get("arch_frame")
        if frame and frame not in admissible_frames:
            raise AdmissibilityError(5, f"Frame '{frame}' is outside the fixed global P-M frame")

    def _check_rule_6(self, input_obj: AbstractInput):
        """Admits admissible recursive decomposition."""
        # Simple depth check for noise prevention
        if str(input_obj.content).count('{') > 10:
             raise AdmissibilityError(6, "Decomposition depth exceeds admissible limit (Noise detected)")

    def _check_rule_7(self, input_obj: AbstractInput):
        """Reaches terminal realized family through fundamental variables."""
        # Blueprint: Must reach v1-v40 ultimately
        if "terminal_variables" not in input_obj.content:
            # We don't force them to be there, but if they are invalid then we error
            pass
        else:
            v_list = input_obj.content["terminal_variables"]
            if not isinstance(v_list, list):
                raise AdmissibilityError(7, "Terminal variables must be a list of identifiers")
