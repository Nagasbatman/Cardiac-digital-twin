#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PULSE API Server Entry Point.

Delegates to the unified multi-module backend at `backend.main`.
Maintains full backward compatibility with existing startup scripts.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from backend.main import app
from backend import config

if __name__ == "__main__":
    print(f"Starting PULSE Unified Backend on http://{config.HOST}:{config.PORT}")
    uvicorn.run("backend.main:app", host=config.HOST, port=config.PORT, reload=False)
