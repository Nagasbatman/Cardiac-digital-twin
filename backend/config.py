"""Configuration for PULSE Backend API Server.
"""
import os
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
CARDIO_TWIN_DIR = BACKEND_DIR / "cardio_twin"

# Ports and network settings
HOST = os.environ.get("PULSE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PULSE_PORT", "8001"))

# CardioSim service URL
CARDIOSIM_URL = os.environ.get("CARDIOSIM_BASE_URL", "http://localhost:8000")

# CORS allowed origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://localhost:8001",
    "*",
]

