"""Configuration for the CardioSim integration layer.

The only setting is the backend base URL.  Override it by setting the
environment variable ``CARDIOSIM_BASE_URL`` before running any code that
imports this module.

Windows PowerShell example::

    $env:CARDIOSIM_BASE_URL = "http://localhost:8000"

The variable is read once at import time so that the value is consistent
for the lifetime of a process.
"""
from __future__ import annotations

import os

#: Default base URL matches the standard CardioSim local-dev port.
_DEFAULT_BASE_URL = "http://localhost:8000"

#: Resolved base URL — set ``CARDIOSIM_BASE_URL`` to override.
BASE_URL: str = os.environ.get("CARDIOSIM_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")

# Connection timeout in seconds (time to establish the TCP connection).
CONNECT_TIMEOUT: float = 5.0

# Read timeout in seconds (maximum wait for the server to return a full response).
# Simulations can take a few seconds, so this is intentionally generous.
READ_TIMEOUT: float = 30.0

