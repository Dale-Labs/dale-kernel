"""
Append-only event store for DALE Kernel runtime events.

Per BuildReference.md Rule 3: "No artifact overwrites history. History is append-only."
Per Boris §14: "The formal history should preserve E_t → E_{t+1} together with the
reason for the transition."

Events are written as JSON lines (one JSON object per line) to
dale-kernel/data/events/{walkthrough_id}/events.jsonl.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data" / "events"


class EventStore:
    """
    Append-only event log.
    
    Events are immutable once written. Each event is a JSON object with:
    - event_id: unique identifier
    - timestamp: ISO 8601 UTC
    - event_type: classification (observation_started, variable_assigned, etc.)
    - walkthrough_id: which WT this belongs to
    - payload: event-specific data
    - sequence_number: monotonically increasing within the walkthrough
    """

    def __init__(self, walkthrough_id: str):
        self.walkthrough_id = walkthrough_id
        self._dir = DATA_DIR / walkthrough_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._dir / "events.jsonl"
        self._seq = self._load_sequence()

    def _load_sequence(self) -> int:
        """Recover the last sequence number from existing events."""
        if not self._log_path.exists():
            return 0
        try:
            with open(self._log_path) as f:
                lines = f.readlines()
            if not lines:
                return 0
            last = json.loads(lines[-1])
            return last.get("sequence_number", len(lines))
        except (json.JSONDecodeError, KeyError, IndexError):
            return 0

    def append(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Append one event to the log. Returns the event_id.
        """
        self._seq += 1
        event = {
            "event_id": f"evt-{self.walkthrough_id}-{self._seq:04d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "walkthrough_id": self.walkthrough_id,
            "sequence_number": self._seq,
            "payload": payload,
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        return event["event_id"]

    def read_all(self) -> List[Dict[str, Any]]:
        """Read all events for this walkthrough in order."""
        if not self._log_path.exists():
            return []
        events = []
        with open(self._log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def read_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Read events filtered by type."""
        return [e for e in self.read_all() if e.get("event_type") == event_type]

    def last_event(self) -> Optional[Dict[str, Any]]:
        """Return the most recent event, or None."""
        events = self.read_all()
        return events[-1] if events else None

    @property
    def event_count(self) -> int:
        return self._seq

    @property
    def log_path(self) -> Path:
        return self._log_path


# ── Standard event types ──────────────────────────────────────────

class EventType:
    """Canonical event type constants."""
    OBSERVATION_STARTED = "observation_started"
    INPUT_ADMITTED = "input_admitted"
    INPUT_REJECTED = "input_rejected"
    VARIABLE_ASSIGNED = "variable_assigned"
    VARIABLE_NON_ASSIGNED = "variable_non_assigned"
    TRACE_CREATED = "trace_created"
    TRACE_LINKED = "trace_linked"
    ECOA_COMPLETED = "ecoa_completed"
    ARA_STARTED = "ara_started"
    ARA_COMPLETED = "ara_completed"
    RESULT_PRODUCED = "result_produced"
    STATE_TRANSITION = "state_transition"
    ERROR = "error"