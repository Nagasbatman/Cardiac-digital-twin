"""In-memory, session-scoped scenario history store.

Features:
- Scoped to an opaque session identifier (UUID) generated per browser session.
- Completely in-memory: no PostgreSQL, no SQLite, no file writes.
- Bounded capacity per session (maximum 20 scenarios) to prevent memory exhaustion.
- LRU/FIFO eviction policy: oldest scenario evicted when session exceeds capacity.
- Thread-safe using a standard mutex lock.
- Clean isolation between concurrent browser sessions: zero data leakage.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from data.scenarios import ScenarioRecord

MAX_SCENARIOS_PER_SESSION = 20
MAX_TRACKED_SESSIONS = 100


class SessionScenarioStore:
    """Thread-safe bounded in-memory storage for what-if scenarios per session."""

    def __init__(
        self,
        max_scenarios_per_session: int = MAX_SCENARIOS_PER_SESSION,
        max_tracked_sessions: int = MAX_TRACKED_SESSIONS,
    ) -> None:
        self._max_scenarios = max_scenarios_per_session
        self._max_sessions = max_tracked_sessions
        # session_id -> OrderedDict[scenario_id, ScenarioRecord]
        self._store: OrderedDict[str, OrderedDict[str, ScenarioRecord]] = OrderedDict()
        self._lock = threading.Lock()

    def add_scenario(self, session_id: str, record: ScenarioRecord) -> None:
        """Add a scenario record to the specified session."""
        if not session_id:
            return

        with self._lock:
            if session_id not in self._store:
                if len(self._store) >= self._max_sessions:
                    # Evict oldest session
                    self._store.popitem(last=False)
                self._store[session_id] = OrderedDict()

            session_records = self._store[session_id]
            scenario_id = record.configuration.scenario_id

            # Add or update
            session_records[scenario_id] = record
            session_records.move_to_end(scenario_id)

            # Enforce max scenarios per session
            while len(session_records) > self._max_scenarios:
                session_records.popitem(last=False)

    def get_scenarios(self, session_id: str) -> list[ScenarioRecord]:
        """Return all scenario records for a session in chronological order."""
        if not session_id:
            return []

        with self._lock:
            if session_id not in self._store:
                return []
            return list(self._store[session_id].values())

    def get_scenario(self, session_id: str, scenario_id: str) -> ScenarioRecord | None:
        """Retrieve a specific scenario record."""
        if not session_id or not scenario_id:
            return None

        with self._lock:
            session_records = self._store.get(session_id)
            if not session_records:
                return None
            return session_records.get(scenario_id)

    def clear_session(self, session_id: str) -> None:
        """Clear all scenarios for a given session."""
        if not session_id:
            return

        with self._lock:
            self._store.pop(session_id, None)

    def total_sessions_count(self) -> int:
        """Total number of active sessions in memory."""
        with self._lock:
            return len(self._store)


# Global singleton instance for the Flask application lifetime
global_scenario_store = SessionScenarioStore()

