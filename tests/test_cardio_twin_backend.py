"""Integration tests for Module III: Cardiovascular Digital Twin in PULSE backend.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDIO_DIR = REPO_ROOT / "backend" / "cardio_twin"

for p in (REPO_ROOT, REPO_ROOT / "pulse", REPO_ROOT / "demo", CARDIO_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.main import app

client = TestClient(app)


def test_health_check_returns_all_three_modules():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "modules" in data
    assert "module_1_mri" in data["modules"]
    assert "module_2_tabular" in data["modules"]
    assert "module_3_digital_twin" in data["modules"]
    assert data["modules"]["module_3_digital_twin"]["prototype_cohort_size"] == 1500


def test_list_patients_returns_cohort_and_curated_samples():
    response = client.get("/api/cardio-twin/patients?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_patients"] == 1500
    assert len(data["patient_ids"]) == 10
    assert len(data["sample_profiles"]) >= 5
    sample_ids = [p["subject_id"] for p in data["sample_profiles"]]
    assert 10009482 in sample_ids


def test_get_patient_profile():
    response = client.get("/api/cardio-twin/patients/10009482")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["subject_id"] == 10009482
    summary = data["summary"]
    assert summary["demographics"]["gender"] == "F"
    assert summary["demographics"]["anchor_age"] == "24"
    assert summary["is_eligible_for_patient_specific"] is False
    assert "lacks documented simulator inputs" in summary["ineligible_reason"]


def test_get_patient_observations_with_pagination():
    response = client.get("/api/cardio-twin/patients/10009482/observations?limit=3&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6
    assert len(data["observations"]) == 3
    first_obs = data["observations"][0]
    assert "measurement_name" in first_obs
    assert "display_name" in first_obs
    assert "usable_for_patient_analysis" in first_obs


def test_get_patient_trends():
    response = client.get("/api/cardio-twin/patients/10009482/trends")
    assert response.status_code == 200
    data = response.json()
    assert data["subject_id"] == 10009482
    assert "trends" in data
    assert len(data["trends"]) > 0


def test_get_patient_analysis():
    response = client.get("/api/cardio-twin/patients/10009482/analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["subject_id"] == 10009482
    assert "analysis" in data
    categories = [c["category"] for c in data["analysis"]]
    assert "Blood Pressure" in categories


def test_get_patient_provenance():
    response = client.get("/api/cardio-twin/patients/10009482/provenance")
    assert response.status_code == 200
    data = response.json()
    prov = data["provenance"]
    assert prov["is_patient_specific_supported"] is False
    assert len(prov["parameters"]) == 4
    param_keys = [p["field_name"] for p in prov["parameters"]]
    assert set(param_keys) == {"hr", "contract", "resist", "compl"}


def test_get_presets_returns_healthy_adult():
    response = client.get("/api/cardio-twin/presets")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Healthy Adult" in data["presets"]
    ha = data["presets"]["Healthy Adult"]
    assert ha["hr"] == 75.0
    assert ha["contract"] == 100.0
    assert ha["resist"] == 1.0
    assert ha["compl"] == 1.46


def test_simulate_preset_executes_successfully():
    response = client.post(
        "/api/cardio-twin/simulate",
        json={
            "subject_id": 10009482,
            "preset_name": "Healthy Adult",
            "duration": 6.0,
        },
        headers={"x-session-id": "test_session_unit"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "metrics" in data
    assert data["metrics"]["co"] > 0
    assert data["metrics"]["ef"] > 0
    assert data["metrics"]["sys"] > 0
    assert data["metrics"]["dia"] > 0


def test_whatif_scenario_rejects_out_of_bounds_parameters():
    # HR > 400 must fail validation
    response = client.post(
        "/api/cardio-twin/scenarios/run",
        json={
            "subject_id": 10009482,
            "scenario_name": "Extreme Tachycardia",
            "preset_name": "Healthy Adult",
            "hr": 999.0,  # Invalid
            "contract": 100.0,
            "resist": 1.0,
            "compl": 1.46,
            "duration": 6.0,
        },
        headers={"x-session-id": "test_session_bounds"},
    )
    assert response.status_code == 422  # FastAPI Pydantic validation error


def test_whatif_scenario_runs_and_computes_deltas():
    session_id = "test_session_deltas"
    response = client.post(
        "/api/cardio-twin/scenarios/run",
        json={
            "subject_id": 10009482,
            "scenario_name": "Elevated Resistance Test",
            "preset_name": "Healthy Adult",
            "hr": 80.0,
            "contract": 105.0,
            "resist": 1.3,
            "compl": 1.40,
            "duration": 6.0,
            "session_id": session_id,
        },
        headers={"x-session-id": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "scenario" in data
    assert "comparison" in data
    deltas = data["comparison"]["deltas"]
    assert len(deltas) == 4
    hr_delta = next(d for d in deltas if d["field_name"] == "hr")
    assert hr_delta["absolute_change"] == 5.0
    assert hr_delta["has_changed"] is True

    # Check scenario history retrieval
    hist_res = client.get("/api/cardio-twin/scenarios", headers={"x-session-id": session_id})
    assert hist_res.status_code == 200
    assert len(hist_res.json()["scenarios"]) >= 1

    # Clear history
    clear_res = client.delete("/api/cardio-twin/scenarios", headers={"x-session-id": session_id})
    assert clear_res.status_code == 200
    cleared_hist = client.get("/api/cardio-twin/scenarios", headers={"x-session-id": session_id})
    assert len(cleared_hist.json()["scenarios"]) == 0

