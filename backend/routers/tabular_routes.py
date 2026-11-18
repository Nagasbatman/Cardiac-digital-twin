"""Module II: Heart Disease Tabular Risk Prediction API routes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

import sys
HEART_TABULAR_DIR = REPO_ROOT / "heart_tabular_module"
if str(HEART_TABULAR_DIR) not in sys.path:
    sys.path.append(str(HEART_TABULAR_DIR))

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

try:
    from src.predict import (
        predict as predict_heart_tabular,
        MODEL as HEART_TABULAR_MODEL,
        REQUIRED_COLUMNS as HEART_REQUIRED_COLUMNS,
    )
    HEART_TABULAR_AVAILABLE = True
except Exception as _ht_err:
    HEART_TABULAR_AVAILABLE = False
    HEART_TABULAR_MODEL = None
    HEART_REQUIRED_COLUMNS = []
    print(f"Warning: Heart Tabular Module failed to initialize: {_ht_err}")

router = APIRouter(tags=["Module II: Tabular Risk"])


class HeartTabularInputModel(BaseModel):
    age: float
    gender: str
    ethnicity: str
    education_level: int
    poverty_income_ratio: float
    bmi: float
    waist_cm: float
    height_cm: float
    systolic_bp: float
    diastolic_bp: float
    resting_heart_rate: float
    total_cholesterol: float
    hdl_cholesterol: float
    hba1c: float
    serum_creatinine: float
    uric_acid: float
    albumin_creatinine_ratio: float
    white_blood_cells: float
    hemoglobin: float
    rdw: float
    smoking_status: str
    physically_active: str
    hypertension_history: str
    high_cholesterol_history: str
    diabetes_status: str
    stroke_history: str
    family_history_chd: str
    general_health: int
    chest_pain_type: str
    severe_chest_pain: str
    sob_on_exertion: str


VALID_GENDERS = {"Female", "Male"}
VALID_ETHNICITIES = {
    "Mexican American", "Non-Hispanic Black", "Non-Hispanic White",
    "Non-Hispanic Asian", "Other Hispanic", "Other/Multi-Racial"
}
VALID_SMOKING = {"Never", "Former", "Current"}
VALID_YES_NO = {"No", "Yes"}
VALID_CHEST_PAIN = {"No pain", "Non-exertional", "Exertional", "Typical angina"}
VALID_EDU_LEVELS = {1, 2, 3, 4, 5}
VALID_HEALTH_LEVELS = {1, 2, 3, 4, 5}


@router.get("/api/heart-tabular/sample")
def get_heart_tabular_sample():
    """Returns reference sample patient for tabular heart disease prediction."""
    sample_file = HEART_TABULAR_DIR / "examples" / "patient.json"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="Tabular heart disease sample patient file not found.")
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read sample patient: {str(e)}")


@router.post("/api/heart-tabular/predict")
async def predict_heart_disease_tabular(patient: HeartTabularInputModel):
    """Executes the independent CDC NHANES Tabular Cardiovascular Disease Model."""
    if not HEART_TABULAR_AVAILABLE or HEART_TABULAR_MODEL is None:
        raise HTTPException(
            status_code=503,
            detail="Heart Tabular Prediction Engine is currently unavailable. Please verify model files on server."
        )

    patient_dict = patient.model_dump()
    errors = []

    if patient_dict["gender"] not in VALID_GENDERS:
        errors.append(f"Invalid gender '{patient_dict['gender']}'. Expected one of: {sorted(VALID_GENDERS)}")
    if patient_dict["ethnicity"] not in VALID_ETHNICITIES:
        errors.append(f"Invalid ethnicity '{patient_dict['ethnicity']}'. Expected one of: {sorted(VALID_ETHNICITIES)}")
    if patient_dict["smoking_status"] not in VALID_SMOKING:
        errors.append(f"Invalid smoking_status '{patient_dict['smoking_status']}'. Expected one of: {sorted(VALID_SMOKING)}")
    if patient_dict["chest_pain_type"] not in VALID_CHEST_PAIN:
        errors.append(f"Invalid chest_pain_type '{patient_dict['chest_pain_type']}'. Expected one of: {sorted(VALID_CHEST_PAIN)}")
    if patient_dict["education_level"] not in VALID_EDU_LEVELS:
        errors.append(f"Invalid education_level '{patient_dict['education_level']}'. Expected integer 1 to 5.")
    if patient_dict["general_health"] not in VALID_HEALTH_LEVELS:
        errors.append(f"Invalid general_health '{patient_dict['general_health']}'. Expected integer 1 to 5.")

    yes_no_fields = [
        "physically_active", "hypertension_history", "high_cholesterol_history",
        "diabetes_status", "stroke_history", "family_history_chd",
        "severe_chest_pain", "sob_on_exertion"
    ]
    for field in yes_no_fields:
        if patient_dict[field] not in VALID_YES_NO:
            errors.append(f"Invalid value '{patient_dict[field]}' for {field}. Expected 'Yes' or 'No'.")

    num_ranges = {
        "age": (18.0, 120.0, "years"),
        "poverty_income_ratio": (0.0, 10.0, "ratio"),
        "bmi": (10.0, 90.0, "kg/m²"),
        "waist_cm": (30.0, 250.0, "cm"),
        "height_cm": (50.0, 260.0, "cm"),
        "systolic_bp": (50.0, 300.0, "mmHg"),
        "diastolic_bp": (30.0, 200.0, "mmHg"),
        "resting_heart_rate": (30.0, 240.0, "bpm"),
        "total_cholesterol": (20.0, 1000.0, "mg/dL"),
        "hdl_cholesterol": (5.0, 200.0, "mg/dL"),
        "hba1c": (2.0, 25.0, "%"),
        "serum_creatinine": (0.1, 20.0, "mg/dL"),
        "uric_acid": (0.5, 30.0, "mg/dL"),
        "albumin_creatinine_ratio": (0.0, 20000.0, "mg/g"),
        "white_blood_cells": (0.1, 100.0, "1000 cells/µL"),
        "hemoglobin": (2.0, 30.0, "g/dL"),
        "rdw": (5.0, 40.0, "%"),
    }
    for field, (min_v, max_v, unit) in num_ranges.items():
        val = patient_dict.get(field)
        if val is None or not (min_v <= float(val) <= max_v):
            errors.append(f"{field} must be between {min_v} and {max_v} {unit} (received {val})")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    try:
        pred = predict_heart_tabular(patient_dict, explain=True)
        factors = []
        if isinstance(pred.explanation, dict) and "factors" in pred.explanation:
            for f in pred.explanation["factors"]:
                eff = float(f.get("effect", 0.0))
                factors.append({
                    "feature": f.get("feature", ""),
                    "value": f.get("value"),
                    "typical": f.get("typical"),
                    "effect": round(eff, 4),
                    "impact": f"{eff * 100:+.1f} pts",
                    "patient_value": f.get("value"),
                    "reference_value": f.get("typical"),
                })

        return {
            "success": True,
            "status": pred.status,
            "label": pred.label,
            "probability": round(float(pred.probability), 4) if pred.probability is not None else None,
            "threshold": float(pred.details.get("threshold", 0.2003)),
            "risk_bands": pred.details.get("risk_bands", {"low": "< 0.2003", "medium": "0.2003 - 0.50", "high": ">= 0.50"}),
            "positive": pred.positive,
            "message": pred.message,
            "factors": factors,
            "details": pred.details,
            "input_summary": patient_dict
        }
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error executing heart tabular prediction model: {str(exc)}"
        )

