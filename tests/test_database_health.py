"""Focused tests for GET /api/database/health.

Covers:
1. Successful database connectivity probe returns HTTP 200 with safe response body.
2. Database connection failure returns HTTP 503 with safe error body.
3. Neither the success nor failure response ever exposes credentials,
   connection URLs, passwords, or raw exception messages.
4. The existing /api/health endpoint is unaffected by either outcome.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENSITIVE_SUBSTRINGS = (
    "password",
    "://",          # any URL scheme
    "postgresql",
    "psycopg",
    "pg8000",
    "localhost",
    "5432",
    "Traceback",
    "OperationalError",
)


def _assert_no_credentials_leaked(body: dict | str) -> None:
    """Fail the test if any sensitive substring appears in the response body."""
    text = str(body).lower()
    for token in _SENSITIVE_SUBSTRINGS:
        assert token.lower() not in text, (
            f"Sensitive token '{token}' found in response body."
        )


# ---------------------------------------------------------------------------
# Test 1: Successful connectivity probe
# ---------------------------------------------------------------------------

def test_database_health_success():
    """GET /api/database/health returns 200 with connected status when DB is reachable."""
    response = client.get("/api/database/health")

    assert response.status_code == 200, (
        f"Expected HTTP 200, got {response.status_code}: {response.text}"
    )

    body = response.json()
    assert body["status"] == "connected", f"Unexpected status: {body}"
    assert "database" in body, "Response must include 'database' field."

    # Must not expose credentials or sensitive internals
    _assert_no_credentials_leaked(body)


# ---------------------------------------------------------------------------
# Test 2: Database connection failure → HTTP 503
# ---------------------------------------------------------------------------

def test_database_health_failure_returns_503():
    """GET /api/database/health returns 503 with safe body when DB is unreachable."""
    # Simulate an OperationalError raised when engine.connect() is called.
    # The mock replaces engine.connect so no real DB call is attempted.
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "could not connect to server",
        params=None,
        orig=Exception("connection refused"),
    )

    with patch("backend.main.engine", mock_engine):
        response = client.get("/api/database/health")

    assert response.status_code == 503, (
        f"Expected HTTP 503, got {response.status_code}: {response.text}"
    )

    body = response.json()
    assert body["status"] == "unavailable", f"Unexpected status field: {body}"
    assert "detail" in body, "Response must include a 'detail' field."

    # Must not expose credentials, stack traces, or raw DB error messages
    _assert_no_credentials_leaked(body)


# ---------------------------------------------------------------------------
# Test 3: Credentials are never present in success response
# ---------------------------------------------------------------------------

def test_database_health_success_no_credentials():
    """Success response must never include credentials or connection details."""
    response = client.get("/api/database/health")
    # Accept 200 (live DB) or 503 (DB down in CI) — only check body safety.
    body = response.json()
    _assert_no_credentials_leaked(body)


# ---------------------------------------------------------------------------
# Test 4: Credentials are never present in failure response
# ---------------------------------------------------------------------------

def test_database_health_failure_no_credentials():
    """Failure response must never include credentials, URLs, or stack traces."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "FATAL: password authentication failed for user \"postgres\"",
        params=None,
        orig=Exception("auth failure"),
    )

    with patch("backend.main.engine", mock_engine):
        response = client.get("/api/database/health")

    assert response.status_code == 503
    body = response.json()
    _assert_no_credentials_leaked(body)


# ---------------------------------------------------------------------------
# Test 5: Existing /api/health is not affected
# ---------------------------------------------------------------------------

def test_existing_health_endpoint_unaffected():
    """/api/health must still return HTTP 200 and its full module-status body."""
    response = client.get("/api/health")

    assert response.status_code == 200, (
        f"/api/health returned {response.status_code}: {response.text}"
    )

    body = response.json()
    assert body["status"] == "healthy"
    assert "modules" in body
    assert "module_1_mri" in body["modules"]
    assert "module_2_tabular" in body["modules"]
    assert "module_3_digital_twin" in body["modules"]


# ---------------------------------------------------------------------------
# Test 6: /api/health is unaffected even when DB is mocked as unavailable
# ---------------------------------------------------------------------------

def test_existing_health_endpoint_unaffected_when_db_down():
    """/api/health must remain operational regardless of database state."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError(
        "connection refused", params=None, orig=Exception()
    )

    with patch("backend.main.engine", mock_engine):
        response = client.get("/api/health")

    # /api/health does not use engine directly, so it must be unaffected.
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"

