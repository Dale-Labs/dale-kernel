"""Typed transport contracts for the API Gateway to Kernel boundary.

Transport and governance metadata remain separate from the formal observation
package and formal DALE result.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .canons import FormalDALEResult


class GatewayRequestEnvelope(BaseModel):
    """Request metadata and source information supplied by an API boundary."""

    contract_version: str = "1.0"
    correlation_id: str
    session_id: str
    user_id: str
    environment: str
    timestamp: datetime
    source_information: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)
    purpose_code: Optional[str] = None
    permission_ref: Optional[str] = None
    idempotency_key: Optional[str] = None


class KernelError(BaseModel):
    """A structured non-completion or processing error."""

    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class KernelResponseEnvelope(BaseModel):
    """Stable response boundary without converting formal output into UI data."""

    contract_version: str = "1.0"
    correlation_id: str
    status: str
    result_id: Optional[str] = None
    observation_id: Optional[str] = None
    formal_result: Optional[FormalDALEResult] = None
    trace_lineage: List[str] = Field(default_factory=list)
    formal_status: Optional[str] = None
    technical_status: Optional[str] = None
    validation_refs: List[str] = Field(default_factory=list)
    application_view_refs: List[str] = Field(default_factory=list)
    errors: List[KernelError] = Field(default_factory=list)

    @classmethod
    def completed(
        cls,
        correlation_id: str,
        result: FormalDALEResult,
    ) -> "KernelResponseEnvelope":
        """Build a completed response from an actual formal result."""
        return cls(
            correlation_id=correlation_id,
            status="complete",
            formal_status="complete",
            technical_status="complete",
            result_id=result.result_id,
            observation_id=result.ecoa_output.observation_id,
            formal_result=result,
            trace_lineage=list(result.trace_path),
        )

    @classmethod
    def rejected(
        cls,
        correlation_id: str,
        errors: List[Dict[str, Any]],
    ) -> "KernelResponseEnvelope":
        """Build a non-completion response without inventing a formal result."""
        return cls(
            correlation_id=correlation_id,
            status="inadmissible",
            formal_status="not_executed",
            technical_status="rejected",
            errors=[KernelError(
                code=f"rule_{error.get('rule', 'unknown')}",
                message=error.get("error", "Input rejected"),
                details=error,
            ) for error in errors],
        )

    def to_json_dict(self) -> Dict[str, Any]:
        """Serialize using Pydantic's JSON-compatible representation."""
        return self.model_dump(mode="json", exclude_none=True)