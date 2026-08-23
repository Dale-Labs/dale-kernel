# DALE Kernel

DALE Kernel is the initial Python execution engine for the DALE ecosystem. It
currently implements the WT-001 coherence-baseline path:

1. Validate an `ObservationPackage` with the current admissibility checks.
2. Create root and child trace objects and link variables to those traces.
3. Classify variables as ECOA-fixed or non-assigned.
4. Write WT-001 runtime events to an append-only JSONL event log.
5. Return a `FormalDALEResult` containing the ECOA output and trace path.

The current implementation is a small, runnable kernel foundation. It is not a
complete DALE platform, API, or seven-walkthrough runtime.

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A fresh checkout of this repository

The project is managed with `uv`. From the repository root:

```bash
uv sync
```

The dependency set currently contains Pydantic 2.x. The checked-in
`.python-version` file selects the project Python version for supported `uv`
workflows.

## Run The Smoke Tests

From `dale-kernel/`, run:

```bash
PYTHONPATH=$PWD uv run python tests/smoke_test.py
```

`PYTHONPATH=$PWD` is required because the source tree is used directly and the
project does not currently define an installable package build configuration.
The command runs the standalone smoke-test runner and should finish with:

```text
14 passed, 0 failed
```

The checks cover:

1. **Admissibility Engine**: accepts a valid structured input and rejects a
	forbidden external reference under Rule 3.
2. **Traceability Factory**: creates root and child traces and links a
	fundamental variable to its trace.
3. **Variable States**: verifies ECOA-fixed, non-assigned, ARA-resolved,
	structurally inactive, and informational-absence states.
4. **ECOA Output Partition**: preserves the disjoint assigned (`V_fix`) and
	non-assigned (`V_na`) variable sets.
5. **Formal DALE Result**: combines an ECOA output with a manually constructed
	ARA output and reports a complete result.
6. **Event Store**: appends, reads, and retrieves ordered JSONL events.
7. **WT-001 Pipeline**: executes a coherent five-variable baseline with no ARA
	stage required.
8. **WT-001 Invalid Input**: rejects a package containing a forbidden external
	reference before execution.
9. **Input Formation**: forms valid, insufficient, ambiguous, and guarded
	packages without inventing missing values.

## Run The WT-001 Demo

From `dale-kernel/`, run:

```bash
PYTHONPATH=$PWD uv run python examples/wt001_demo.py
```

The demo creates a WT-001 baseline with 40 coherent fundamental variables and
prints the result ID, completion status, ECOA partition, ARA requirement,
event count, runtime state, and variable summary. A successful run ends with:

```text
WT-001 pipeline executed successfully.
```

Runtime events are stored under `data/events/<walkthrough-id>/events.jsonl`.
The event store is append-only, so repeated runs for the same walkthrough add
events to the existing log rather than replacing its history.

## Production Entrypoint

`main.py` does not create demo data or invent an observation package. The
production boundary is `execute_observation(package, variables)`, which accepts
an already-formed package from an API, input-formation service, or other caller
and passes it to the Kernel engine. Running `main.py` only prints the available
entrypoint and the commands for the demo and smoke tests.

The hardcoded WT-001 fixture lives in `examples/wt001_demo.py`. Verification
fixtures and assertions live in `tests/smoke_test.py`.

## Current Status

### Implemented

- Pydantic models for observation conditions, inputs, packages, variables,
  traces, ECOA output, ARA output, and formal results.
- Fellowship-aligned pre-ECOA boundary models for project sources,
  structural declarations, Project-to-ECOA bridge records, architecture
	review, candidate admission decisions, and formal input-package closure.
- A pre-ECOA `InputFormationService` that preserves missingness, ambiguity,
	source references, and formation status before package admission.
- Typed API Gateway request and Kernel response envelopes in
	`src/dale_kernel/core/contracts.py`; these keep transport metadata separate
	from the formal observation package and result, including separate formal and
	technical status fields.
- A basic admissibility engine covering the current Rule 2 through Rule 7
  checks. Pydantic validation handles basic input shape constraints.
- Root and parent-child trace creation with variable linking.
- An append-only JSONL event store with sequence numbers and standard event
  types.
- The WT-001 execution path through admissibility, traceability, state
  resolution, event logging, and formal result creation.
- ECOA value-origin metadata for values assigned by the current WT-001 path;
	ARA origin is reserved for future Stage 2 completion.
- Standalone smoke coverage for the fourteen checks listed above.

### Not Implemented

The following are not currently complete and should not be treated as
available runtime features:

- WT-002 missingness handling
- WT-003 contradiction handling
- WT-004 governance-fracture handling
- WT-005 adaptation handling
- WT-006 memory/history behavior beyond the event log
- WT-007 combined-stress handling
- AI-assisted source-to-input formation and vocabulary mapping
- Formal ECOA input closure predicates beyond the initial boundary checks
- ARA completion logic or a constrained ARA solver
- A Read/snapshot generator
- An API or API gateway
- Production persistence, deployment, or the planned AWS platform integration

The current WT-001 resolver assumes a coherent baseline. If non-assigned
variables are supplied, it marks the runtime degraded and records an error
event; it does not solve them through ARA. Admissibility rules are an initial
implementation rather than a complete formal enforcement of every Canon
constraint, and the current test coverage is smoke-level rather than a full
unit or integration suite.
