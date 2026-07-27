"""Run the explicit WT-001 demonstration fixture."""

from src.dale_kernel.core.canons import (
    AbstractInput,
    EngagementType,
    ObservationCondition,
    ObservationMode,
    ObservationPackage,
)
from src.dale_kernel.core.engine import DALEKernel
from src.dale_kernel.services.state_resolver import StateResolver


def main() -> None:
    print("DALE Kernel - WT-001 Coherence Baseline Demo")
    print("=" * 50)

    condition = ObservationCondition(
        sector="demo",
        geography="test-environment",
        engagement_type=EngagementType.LEVEL3_PLATFORM,
        observation_mode=ObservationMode.MIXED,
    )
    package = ObservationPackage(
        walkthrough_id="WT-001",
        scenario_type="Baseline",
        inputs=[AbstractInput(
            source_actor="DemoActor",
            content={"arch_frame": "P1", "description": "WT-001 baseline demo"},
        )],
        observation_condition=condition,
    )

    kernel = DALEKernel(package.walkthrough_id)
    result, errors = kernel.execute(
        package,
        StateResolver.make_coherent_variables(count=40),
    )

    if errors:
        raise SystemExit(f"Admissibility errors: {errors}")

    print(f"Result ID: {result.result_id}")
    print(f"Complete: {result.is_complete}")
    print(f"ECOA assigned: {len(result.ecoa_output.assigned_variables)}")
    print(f"ECOA non-assigned: {len(result.ecoa_output.non_assigned_variables)}")
    print(f"ARA required: {result.ara_output is not None}")
    print(f"Events logged: {kernel.event_count}")
    print(f"Current state: {kernel.current_state.value}")
    print(f"Variable summary: {result.variable_summary}")
    print("\nWT-001 pipeline executed successfully.")


if __name__ == "__main__":
    main()