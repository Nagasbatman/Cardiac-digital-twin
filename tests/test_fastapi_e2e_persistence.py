"""End-to-End FastAPI Application Persistence & Behavior Verification.

Validates:
1. Module I (MRI Analysis), Module II (Tabular Risk), Module III (CardioSim Digital Twin) endpoints.
2. Verification of 1:1 database records in pulse.analysis_runs and child tables.
3. Verification that failed requests do not create database records.
4. Verification that anonymous requests work without inventing patient identities.
5. Verification that patient associations are never invented from untrusted identifiers.
6. Verification that clinical API responses remain intact if database operations fail.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.main import app
from backend.db.session import SessionLocal
from backend.db.models import AnalysisRun, MriAnalysis, Patient, RiskAssessment, SimulationRun

client = TestClient(app)


# ---------------------------------------------------------------------------
# Module II: Heart Tabular Risk Prediction
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_tabular_payload():
    return {
        "age": 58.0,
        "gender": "Female",
        "ethnicity": "Non-Hispanic White",
        "education_level": 4,
        "poverty_income_ratio": 3.2,
        "bmi": 26.5,
        "waist_cm": 82.0,
        "height_cm": 165.0,
        "systolic_bp": 128.0,
        "diastolic_bp": 78.0,
        "resting_heart_rate": 68.0,
        "total_cholesterol": 195.0,
        "hdl_cholesterol": 55.0,
        "hba1c": 5.4,
        "serum_creatinine": 0.8,
        "uric_acid": 4.8,
        "albumin_creatinine_ratio": 8.0,
        "white_blood_cells": 5.9,
        "hemoglobin": 13.8,
        "rdw": 12.5,
        "smoking_status": "Never",
        "physically_active": "Yes",
        "hypertension_history": "No",
        "high_cholesterol_history": "No",
        "diabetes_status": "No",
        "stroke_history": "No",
        "family_history_chd": "No",
        "general_health": 2,
        "chest_pain_type": "No pain",
        "severe_chest_pain": "No",
        "sob_on_exertion": "No",
    }


def test_tabular_risk_api_success_and_db_persistence(valid_tabular_payload):
    """Successful tabular prediction creates exactly one analysis_run and one risk_assessment."""
    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    assessments_before = db.query(RiskAssessment).count()
    db.close()

    response = client.post("/api/heart-tabular/predict", json=valid_tabular_payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify API response contract is preserved
    assert data["success"] is True
    assert "status" in data
    assert "label" in data
    assert "probability" in data
    assert "threshold" in data
    assert "factors" in data

    # Verify Database Records
    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        assessments_after = db.query(RiskAssessment).count()
        assert runs_after == runs_before + 1
        assert assessments_after == assessments_before + 1

        # Retrieve the latest run
        latest_run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        assert latest_run is not None
        assert latest_run.module_type == "tabular_risk"
        assert latest_run.status == "SUCCESS"
        assert latest_run.risk_assessment is not None
        assert latest_run.risk_assessment.run_id == latest_run.id
        assert latest_run.risk_assessment.risk_label == data["label"]
        assert round(latest_run.risk_assessment.risk_probability, 4) == round(data["probability"], 4)
        assert round(latest_run.risk_assessment.threshold, 4) == round(data["threshold"], 4)

        # Anonymous survey request: patient_id must be None (no invented identity)
        assert latest_run.patient_id is None
    finally:
        db.close()


def test_tabular_risk_api_validation_failure_no_db_record(valid_tabular_payload):
    """Failed requests (HTTP 400) must NOT create any database records."""
    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    assessments_before = db.query(RiskAssessment).count()
    db.close()

    # Pass invalid payload (negative age and unknown gender)
    invalid_payload = dict(valid_tabular_payload)
    invalid_payload["age"] = -10.0
    invalid_payload["gender"] = "UnknownGender"

    response = client.post("/api/heart-tabular/predict", json=invalid_payload)
    assert response.status_code == 400

    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        assessments_after = db.query(RiskAssessment).count()
        assert runs_after == runs_before
        assert assessments_after == assessments_before
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Module III: CardioSim Digital Twin Simulation
# ---------------------------------------------------------------------------

def test_cardiosim_simulation_api_success_and_db_persistence():
    """Successful CardioSim preset simulation creates analysis_run and simulation_run records."""
    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    sims_before = db.query(SimulationRun).count()
    db.close()

    payload = {
        "subject_id": 10009482,
        "preset_name": "Healthy Adult",
        "duration": 6.0,
    }
    response = client.post("/api/cardio-twin/simulate", json=payload, headers={"x-session-id": "e2e_test_session"})
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify API response contract
    assert data["success"] is True
    assert "metrics" in data
    assert "co" in data["metrics"]
    assert "ef" in data["metrics"]
    assert "scenario_label" in data

    # Verify Database Records
    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        sims_after = db.query(SimulationRun).count()
        assert runs_after == runs_before + 1
        assert sims_after == sims_before + 1

        latest_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.module_type == "cardio_twin")
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        assert latest_run is not None
        assert latest_run.status == "SUCCESS"
        assert latest_run.simulation_run is not None
        assert latest_run.simulation_run.run_id == latest_run.id
        assert latest_run.simulation_run.preset_name == "Healthy Adult"
        assert latest_run.simulation_run.scenario_kind == "GENERIC_BASELINE"
        assert latest_run.simulation_run.session_id == "e2e_test_session"
        assert latest_run.simulation_run.metrics["co"] == data["metrics"]["co"]

        # Verified MIMIC Prototype Patient was safely linked
        assert latest_run.patient is not None
        assert latest_run.patient.source_system == "MIMIC_PROTOTYPE"
        assert latest_run.patient.patient_identifier == "10009482"
    finally:
        db.close()


def test_cardiosim_anonymous_whatif_scenario_persistence():
    """Anonymous what-if scenario (subject_id=None) persists with patient_id=None."""
    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    sims_before = db.query(SimulationRun).count()
    db.close()

    payload = {
        "scenario_name": "Anonymous Resistance Test",
        "preset_name": "Healthy Adult",
        "hr": 85.0,
        "contract": 100.0,
        "resist": 1.4,
        "compl": 1.2,
        "duration": 6.0,
        "subject_id": None,
    }
    response = client.post("/api/cardio-twin/scenarios/run", json=payload, headers={"x-session-id": "anon_session"})
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["success"] is True
    assert "scenario" in data

    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        sims_after = db.query(SimulationRun).count()
        assert runs_after == runs_before + 1
        assert sims_after == sims_before + 1

        latest_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.module_type == "cardio_twin")
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        assert latest_run.simulation_run.scenario_kind == "WHAT_IF"
        # Anonymous scenario must NOT invent a patient
        assert latest_run.patient_id is None
    finally:
        db.close()


def test_cardiosim_validation_failure_no_db_record():
    """Out-of-bounds parameters reject (HTTP 400) without database record creation."""
    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    db.close()

    payload = {
        "scenario_name": "Invalid HR Scenario",
        "preset_name": "Healthy Adult",
        "hr": 999.0,  # Max allowed is 400
        "contract": 100.0,
        "resist": 1.0,
        "compl": 1.46,
        "duration": 6.0,
    }
    response = client.post("/api/cardio-twin/scenarios/run", json=payload)
    assert response.status_code in (400, 422)

    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        assert runs_after == runs_before
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Module I: Cardiac MRI Analysis
# ---------------------------------------------------------------------------

def test_mri_analysis_sample_mode_persistence():
    """Executes bundled Patient 101 sample case and verifies database persistence."""
    sample_dir = REPO_ROOT.parent / "ACDC" / "database" / "testing" / "patient101"
    if not sample_dir.exists():
        pytest.skip(f"MRI sample case patient101 not present at {sample_dir}")

    db = SessionLocal()
    runs_before = db.query(AnalysisRun).count()
    mri_before = db.query(MriAnalysis).count()
    db.close()

    response = client.post(
        "/api/analyze",
        data={
            "mode": "sample",
            "tta_enabled": "false",
            "height_cm": "170.0",
            "weight_kg": "70.0",
            "user_confirmed": "true",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["success"] is True
    assert "metadata" in data
    assert "diagnosis" in data
    assert "biomarkers" in data
    assert "slices" in data

    db = SessionLocal()
    try:
        runs_after = db.query(AnalysisRun).count()
        mri_after = db.query(MriAnalysis).count()
        assert runs_after == runs_before + 1
        assert mri_after == mri_before + 1

        latest_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.module_type == "mri")
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        assert latest_run is not None
        assert latest_run.status == "SUCCESS"
        assert latest_run.mri_analysis is not None
        assert latest_run.mri_analysis.run_id == latest_run.id
        assert latest_run.mri_analysis.predicted_class == data["diagnosis"]["predicted_class"]

        # Verify that unverified metadata does not invent a patient identity
        is_verified = data["metadata"].get("patient_id_verified", False)
        if not is_verified:
            assert latest_run.patient_id is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Decoupled Fail-Safe Database Failure Handling
# ---------------------------------------------------------------------------

def test_database_failure_does_not_interrupt_api_response(valid_tabular_payload):
    """Verifies that an unexpected database failure never interrupts or fails the clinical API response."""
    with patch("backend.db.persistence.SessionLocal", side_effect=Exception("Simulated Database Outage")):
        response = client.post("/api/heart-tabular/predict", json=valid_tabular_payload)
        # Clinical response must succeed regardless of database state
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "probability" in data
        assert "label" in data

