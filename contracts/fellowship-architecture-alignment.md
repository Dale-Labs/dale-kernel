# Fellowship Architecture Alignment

**Status:** Working implementation record  
**Updated:** 2026-08-22

## Source Hierarchy

1. DALE Fellowship Formal Architecture: formal and mathematical authority.
2. DALE Fellowship Implementation Profile v0: implementation-conformance requirements.
3. API Gateway / Jielekeze flow: working transport and application proposal.
4. Existing Kernel and Reads code: current implementation, not architectural authority.

## Implemented Boundary Slice

The Kernel now represents the pre-ECOA boundary as:

```text
ProjectSource
  -> StructuralDeclaration
  -> BridgeRecord
  -> FormalInputPackage
  -> ObservationCondition
```

The package does not assign ECOA or ARA values. It can only become reliable
when the structural declaration and Project-to-ECOA bridge are closed, the
formal package is populated, and the source-to-bridge trace is present.

## Discrepancies With Earlier API Flow

| Earlier API flow | Fellowship requirement | Current decision |
|---|---|---|
| Input formation directly produces an ECOA-ready package | A structural declaration and typed Project-to-ECOA bridge must be closed first | API-formed data remains pending or requires architecture review until closure |
| Missing or unclear data can be represented as incomplete input | Architecture insufficiency is distinct from informational absence and non-assignment | Architecture insufficiency routes to review, not ARA |
| API response may expose `JijueResult` after formal processing | Formal, pathway, lateral, and application results are separate objects | Kernel returns formal result only; application translation remains downstream |
| Example mappings such as `transport -> transport_informal` appear in the flow | Formal mappings require declared support and versioning | Mappings are references, not hardcoded Kernel meaning |
| ARA example resembles a recommendation | ARA completion must remain distinct from application translation | No Grace-specific ARA values are implemented yet |

## Next Required Decisions

- Confirm the canonical structural classes, active roles, and representation modes.
- Confirm the bridge mapping vocabulary and version ownership.
- Define the predicates that close a declaration and bridge.
- Confirm the formal origin model for ECOA-assigned and ARA-completed values.
- Define separate formal, pathway-validation, lateral-validation, and application-result contracts.
- Add a Kernel-to-Reads adapter only after the formal result contract is stable.

## Current Limit

This slice improves architectural visibility and boundary reliability. It does
not implement ECOA mathematics, ARA completion, pathway validation, lateral
validation, or application translation.