"""PULSE Unified Backend API Server.

Integrates:
- Module I: Cardiovascular MRI Analysis (4-Fold ViT-B/14 DINOv2 Ensemble & Random Forest Classifier)
- Module II: Heart Disease Tabular Risk Prediction (CDC NHANES Calibrated Classifier)
- Module III: Cardiovascular Digital Twin & CardioSim Simulation Engine (1,500 MIMIC Cohort & ODE Solver)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure paths
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
CARDIO_DIR = BACKEND_DIR / "cardio_twin"

for p in (REPO_ROOT, REPO_ROOT / "pulse", REPO_ROOT / "demo", CARDIO_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.routers.mri_routes import router as mri_router
from backend.routers.tabular_routes import router as tabular_router, HEART_TABULAR_AVAILABLE
from backend.routers.cardio_twin_routes import router as cardio_twin_router, _loader, _get_cardiosim_client

app = FastAPI(
    title="PULSE Unified Cardiac Digital Twin API",
    description="Multi-modal cardiovascular research platform: MRI segmentation, tabular risk prediction, and lumped-parameter digital twin simulation.",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all 3 modules
app.include_router(mri_router)
app.include_router(tabular_router)
app.include_router(cardio_twin_router)


@app.get("/api/health")
def health():
    """Unified telemetry and system health across all three integrated modules."""
    # Module 1 Check
    folds_dir = REPO_ROOT / "checkpoints" / "folds_vdino"
    models_ready = True
    try:
        for fold in range(4):
            if not (folds_dir / f"fold_{fold}" / "best_model.pth").exists():
                models_ready = False
                break
    except Exception:
        models_ready = False

    # Module 3 Checks
    cardiosim_ready = False
    presets_count = 0
    try:
        client = _get_cardiosim_client()
        presets = client.get_presets()
        cardiosim_ready = True
        presets_count = len(presets)
    except Exception:
        cardiosim_ready = False

    prototype_patients_count = 0
    try:
        prototype_patients_count = _loader.get_patient_count()
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "PULSE Unified Cardiac Digital Twin API",
        "port": config.PORT,
        "modules": {
            "module_1_mri": {
                "name": "Cardiovascular MRI Analysis",
                "ready": models_ready,
                "folds": [0, 1, 2, 3],
            },
            "module_2_tabular": {
                "name": "Heart Disease Tabular Risk Prediction",
                "ready": HEART_TABULAR_AVAILABLE,
            },
            "module_3_digital_twin": {
                "name": "Cardiovascular Digital Twin & Simulation",
                "ready": cardiosim_ready and prototype_patients_count > 0,
                "cardiosim_ready": cardiosim_ready,
                "presets_available": presets_count,
                "prototype_cohort_size": prototype_patients_count,
            },
        },
    }


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=config.HOST, port=config.PORT, reload=False)

