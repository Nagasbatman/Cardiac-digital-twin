"""Integration test for PULSE PostgreSQL schema persistence.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest
from dotenv import load_dotenv

import sys
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from backend.db.session import SessionLocal, get_database_url
from backend.db.models import AnalysisRun, MriAnalysis, Patient, RiskAssessment, SimulationRun
from backend.db.persistence import (
    persist_mri_analysis_run,
    persist_tabular_risk_run,
    persist_simulation_run,
)


def test_postgres_connection_and_schema():
    """Verify connection and that pulse schema tables are accessible via ORM."""
    db = SessionLocal()
    try:
        patients_count = db.query(Patient).count()
        assert patients_count >= 0
        runs_count = db.query(AnalysisRun).count()
        assert runs_count >= 0
    finally:
        db.close()


def test_persist_tabular_risk_run():
    """Test persisting Module 2 Tabular Risk output."""
    sample_input = {
        "age": 55.0,
        "gender": "Male",
        "ethnicity": "Non-Hispanic White",
        "education_level": 3,
        "poverty_income_ratio": 2.5,
        "bmi": 28.4,
        "waist_cm": 95.0,
        "height_cm": 178.0,
        "systolic_bp": 135.0,
        "diastolic_bp": 85.0,
        "resting_heart_rate": 72.0,
        "total_cholesterol": 210.0,
        "hdl_cholesterol": 45.0,
        "hba1c": 5.8,
        "serum_creatinine": 0.9,
        "uric_acid": 5.5,
        "albumin_creatinine_ratio": 12.0,
        "white_blood_cells": 6.8,
        "hemoglobin": 15.2,
        "rdw": 13.0,
        "smoking_status": "Former",
        "physically_active": "Yes",
        "hypertension_history": "Yes",
        "high_cholesterol_history": "No",
        "diabetes_status": "No",
        "stroke_history": "No",
        "family_history_chd": "Yes",
        "general_health": 3,
        "chest_pain_type": "No pain",
        "severe_chest_pain": "No",
        "sob_on_exertion": "No",
    }
    sample_result = {
        "success": True,
        "status": "VALID",
        "label": "Low Risk",
        "probability": 0.1425,
        "threshold": 0.2003,
        "positive": False,
        "factors": [{"feature": "systolic_bp", "value": 135.0, "typical": 120.0, "effect": 0.03}],
    }

    run_id = persist_tabular_risk_run(sample_result, sample_input, execution_time_ms=45.2)
    assert run_id is not None

    db = SessionLocal()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        assert run is not None
        assert run.module_type == "tabular_risk"
        assert run.status == "SUCCESS"
        assert run.risk_assessment is not None
        assert run.risk_assessment.risk_label == "Low Risk"
        assert run.risk_assessment.risk_probability == 0.1425
        assert run.risk_assessment.threshold == 0.2003
        assert run.risk_assessment.positive is False
    finally:
        db.close()


def test_persist_simulation_run():
    """Test persisting Module 3 Digital Twin CardioSim simulation output."""
    run_id = persist_simulation_run(
        scenario_name="Hypertension Challenge Test",
        scenario_kind="GENERIC_BASELINE",
        preset_name="Hypertension",
        sim_params={"hr": 80.0, "contract": 110.0, "resist": 1.5, "compl": 1.1},
        metrics={"co": 4.2, "sv": 52.5, "sys": 142.0, "dia": 96.0, "map_val": 111.0, "pp": 46.0, "ef": 58.0, "hr": 80.0},
        deltas=[],
        subject_id=10009482,
        session_id="test_unit_session_123",
        execution_time_ms=88.5,
    )
    assert run_id is not None

    db = SessionLocal()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        assert run is not None
        assert run.module_type == "cardio_twin"
        assert run.simulation_run is not None
        assert run.simulation_run.preset_name == "Hypertension"
        assert run.simulation_run.scenario_kind == "GENERIC_BASELINE"
        assert run.simulation_run.metrics["map_val"] == 111.0
        # Verify patient was safely recorded with source_system partition
        assert run.patient is not None
        assert run.patient.source_system == "MIMIC_PROTOTYPE"
        assert run.patient.patient_identifier == "10009482"
    finally:
        db.close()


def test_persist_mri_run():
    """Test persisting Module 1 MRI volumetric segmentation output."""
    sample_mri_res = {
        "success": True,
        "metadata": {
            "patient_id": "101",
            "patient_id_verified": True,
            "height_cm": 170.0,
            "weight_kg": 70.0,
            "patient_bsa": 1.81,
            "num_slices": 10,
            "dimensions": [256, 256, 10],
            "voxel_spacing": [1.4, 1.4, 10.0],
            "tta_enabled": False,
        },
        "diagnosis": {
            "predicted_class": "DCM",
            "predicted_full_name": "Dilated Cardiomyopathy",
            "confidence": 92.4,
            "probabilities": {"NOR": 0.02, "DCM": 0.924, "HCM": 0.01, "MINF": 0.03, "RV": 0.016},
        },
        "biomarkers": [
            {"key": "LV_EDV", "name": "Left Ventricle End-Diastolic Volume", "value": 210.5, "unit": "mL"},
            {"key": "LV_EF", "name": "Left Ventricle Ejection Fraction", "value": 32.0, "unit": "%"},
        ],
    }

    run_id = persist_mri_analysis_run(sample_mri_res, mode="sample", execution_time_ms=1200.0)
    assert run_id is not None

    db = SessionLocal()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        assert run is not None
        assert run.module_type == "mri"
        assert run.mri_analysis is not None
        assert run.mri_analysis.predicted_class == "DCM"
        assert run.mri_analysis.confidence == 92.4
        assert run.patient is not None
        assert run.patient.source_system == "MRI_SAMPLE"
        assert run.patient.patient_identifier == "101"
    finally:
        db.close()
