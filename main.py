"""Production-facing entrypoint for the DALE Kernel."""

from typing import List, Tuple

from src.dale_kernel.core.canons import FundamentalVariable, FormalDALEResult, ObservationPackage
from src.dale_kernel.core.engine import DALEKernel


def execute_observation(
    package: ObservationPackage,
    variables: List[FundamentalVariable],
) -> Tuple[FormalDALEResult, List[dict]]:
    """Execute one caller-supplied observation package through the kernel."""
    return DALEKernel(package.walkthrough_id).execute(package, variables)


def main() -> int:
    """Describe the production entrypoint without inventing observation data."""
    print("DALE Kernel entrypoint")
    print("Provide an ObservationPackage and variables to execute_observation().")
    print("Demo:    PYTHONPATH=$PWD uv run python examples/wt001_demo.py")
    print("Tests:   PYTHONPATH=$PWD uv run python tests/smoke_test.py")
    return 0


if __name__ == "__main__":
    main()
