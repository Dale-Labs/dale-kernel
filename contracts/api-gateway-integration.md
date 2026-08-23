# API Gateway ↔ DALE Kernel Integration Contract

**Version:** 1.0  
**Date:** 2026-08-04  
**Status:** Draft — awaiting Vidhi's review

---

## 1. Purpose

This document defines the formal contract between the **Kadana API Gateway** (Vidhi Doshi) and the **DALE Kernel** (Nirjal Shakya). It specifies:

- What data crosses the boundary in each direction
- What validations each side is responsible for
- What the Kernel guarantees vs. what the Gateway guarantees
- How results are persisted to `dale-reads`

---

## 2. Architectural Separation (from Shared Gateway Executive Summary)

| Layer | Responsibility | Must NOT do |
| :--- | :--- | :--- |
| **API Gateway** | Identity, access, validation, routing, versioning, trace propagation, typed responses | Independently determine formal empirical meaning, generate ECOA assignments, perform ARA completion |
| **DALE Kernel** | ECOA observation, ARA completion, formal result generation | Invent source information, silently construct observation conditions, collapse authoritative results into application objects |
| **dale-reads** | Immutable persistence, signal management, historical indexing | Execute DALE mathematics, assign variables |

---

## 3. Request Flow

```
User → Kadana API → InputFormationService → AdmissibilityEngine → StateResolver (ECOA) → [ARA Stage 2] → FormalDALEResult → dale-reads
                                                                                                      ↓
                                                                                                Kadana API ← JijueResult
```

---

## 4. Input Contract: API → Kernel

### 4.1 Trigger

`POST /jitambulishe/sessions/{session_id}/complete`

When a user completes the Check My Hustle survey, the API sends the assessment data to the Kernel.

### 4.2 Request Envelope

```json
{
  "correlation_id": "uuid",
  "session_id": "string",
  "user_id": "string",
  "environment": "jielekeze",
  "timestamp": "2026-08-04T12:00:00Z",
  "source_information": {
    "goal": "string",
    "blockers": ["string"],
    "aspiration_text": "string",
    "county": "string",
    "ward": "string",
    "age_range": "string | null",
    "work_type": "string | null"
  },
  "context": {
    "county": "string",
    "ward": "string",
    "knowledge_refs": ["string (optional knowledge resource IDs)"]
  }
}
```

### 4.3 Gateway Responsibilities (before sending to Kernel)

- [ ] Validate JWT / session ownership
- [ ] Verify session status is `in_progress` and all steps completed
- [ ] Attach `correlation_id` for trace propagation
- [ ] Attach `environment` identifier (jielekeze, ape, sve)
- [ ] Route to correct Kernel endpoint

### 4.4 Kernel Responsibilities (on receipt)

- [ ] Run `InputFormationService`: structure raw responses into `FormedInput`
- [ ] Run `AdmissibilityEngine`: validate against 7 admissibility rules
- [ ] If inadmissible: return `Status` output with reason (do not invent)
- [ ] If admissible: proceed to ECOA observation

---

## 5. Output Contract: Kernel → API

### 5.1 Success Response

```json
{
  "correlation_id": "uuid",
  "result_id": "uuid",
  "observation_id": "uuid",
  "trace_id": "uuid",
  "status": "complete",
  "jijue_result": {
    "summary": {
      "traits": ["string"],
      "top_blockers": ["string"]
    },
    "possible_pathways": ["string"],
    "what_others_are_trying": ["string"],
    "social_proof": "string",
    "recommended_group_id": "string | null",
    "recommended_program_id": "string | null",
    "dashboard_url": "string"
  },
  "trace_lineage": {
    "source_to_result": [
      "source:session/{session_id}",
      "formed_input:{input_id}",
      "package:{package_id}",
      "ecoa:{observation_id}",
      "result:{result_id}"
    ]
  }
}
```

### 5.2 Non-Completion Responses

The Kernel may return status outputs instead of a full result:

| Status | Meaning | API Action |
| :--- | :--- | :--- |
| `insufficient_information` | Missing required fields, unresolvable ambiguity | Prompt user for clarification |
| `inadmissible` | Input violates admissibility rules | Log, notify, do not retry with same input |
| `contradiction_visible` | Competing values detected | Preserve both, flag for human review |
| `missingness_preserved` | Variables intentionally left unresolved | Store as degraded state, continue |
| `paused` | Process requires human governance decision | Queue for review |

### 5.3 Kernel Guarantees

- Every response includes `correlation_id` matching the request
- Every `result_id` is linked to an immutable Read in `dale-reads`
- The Kernel will never invent values for missing fields
- The Kernel will never silently resolve contradictions
- All outputs are traceable back to source information

---

## 6. Persistence Contract: Kernel → dale-reads

### 6.1 Storage Path

```
dale-reads/reads/{year}/{quarter}/READ-{result_id}.json
```

### 6.2 Stored Object

The full `FormalDALEResult` including:
- `ECOAOutput` (observation data, assigned/non-assigned partitions)
- `ARAOutput` (completion data, when Stage 2 is implemented)
- Complete trace lineage
- Event log

### 6.3 Signal Update

On successful persistence, `active-signal.json` is updated:
```json
{
  "current_signal": "SIGNAL-{year}-{quarter}",
  "last_result_id": "{result_id}",
  "last_observation_id": "{observation_id}",
  "timestamp": "ISO8601"
}
```

---

## 7. Error Contract

### 7.1 Gateway Errors (before Kernel)

| HTTP Status | Meaning |
| :--- | :--- |
| 401 | Invalid/missing JWT |
| 403 | Session does not belong to user |
| 404 | Session not found |
| 409 | Session already completed |
| 422 | Missing required steps |

### 7.2 Kernel Errors

| Status | Meaning |
| :--- | :--- |
| `inadmissible` | Input failed admissibility checks |
| `trace_failure` | Trace lineage could not be preserved |
| `metric_incompatibility` | Systems operate under incompatible metrics |
| `weighting_failure` | Required weighting regime absent |
| `insufficient_guidance_space` | Cannot select valid guiding movement |

---

## 8. Open Questions for Vidhi

1. Is the `source_information` schema above complete, or are there additional fields from the survey?
2. Should the Kernel return `JijueResult` directly, or should the API compose it from a more granular Kernel response?
3. What's the expected latency SLA? (ECOA observation may be computationally intensive)
4. Should `knowledge_refs` (from `GET /knowledge`) be passed as context to improve observation quality?
5. Where does the `dashboard_url` come from — is it generated by the Kernel or the API?

---

## 9. Versioning

- Contract version is included in every request/response
- Breaking changes require a new contract version
- The Kernel must support the previous contract version for a deprecation period