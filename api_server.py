#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULSE Backend API Server
========================
Provides high-performance, asynchronous REST API endpoints for the Next.js frontend.
Reuses the exact pretrained 4-fold ensemble (folds 0-3) and Random Forest classifier
from demo/app.py without duplicating machine learning code or modifying existing checkpoints.
"""

import os
import sys
import tempfile
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure PULSE and demo directories are in sys.path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pulse"))
sys.path.insert(0, str(REPO_ROOT / "demo"))

import numpy as np
import nibabel as nib
import cv2
import torch
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import get_models, get_classifier, infer_3d_volume, make_overlay, DEVICE, IMG_SIZE
from diagnosis_features import biomarkers, bsa_dubois, FEAT_KEYS, CLS_NAMES
from validation import (
    ValidationError,
    validate_pulse_inputs,
    find_and_parse_info_cfg,
    PhaseStatus,
)

# Tabular heart prediction module (appended to sys.path so it does not shadow demo/app)
HEART_TABULAR_DIR = REPO_ROOT / "heart_tabular_module"
if str(HEART_TABULAR_DIR) not in sys.path:
    sys.path.append(str(HEART_TABULAR_DIR))

import json
import warnings
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

app = FastAPI(
    title="PULSE Cardiac Digital Twin API",
    description="REST API adapter for Next.js frontend connecting to the PULSE segmentation & diagnosis engine",
    version="1.0.0"
)

# Enable CORS for local Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BIOMARKER_META = {
    "LV_EDV": {"description": "Left Ventricle End-Diastolic Volume", "unit": "mL", "category": "LV Function", "normal": "100 - 180 mL"},
    "LV_ESV": {"description": "Left Ventricle End-Systolic Volume", "unit": "mL", "category": "LV Function", "normal": "30 - 70 mL"},
    "LV_SV": {"description": "Left Ventricle Stroke Volume", "unit": "mL", "category": "LV Function", "normal": "60 - 110 mL"},
    "LV_EF": {"description": "Left Ventricle Ejection Fraction", "unit": "%", "category": "LV Function", "normal": "55 - 75 %"},
    "LVM": {"description": "Left Ventricular Myocardial Mass", "unit": "g", "category": "Myocardium", "normal": "90 - 160 g"},
    "Myo_ED": {"description": "Myocardium Volume at ED", "unit": "mL", "category": "Myocardium", "normal": "75 - 140 mL"},
    "Myo_ES": {"description": "Myocardium Volume at ES", "unit": "mL", "category": "Myocardium", "normal": "75 - 140 mL"},
    "RV_EDV": {"description": "Right Ventricle End-Diastolic Volume", "unit": "mL", "category": "RV Function", "normal": "100 - 200 mL"},
    "RV_ESV": {"description": "Right Ventricle End-Systolic Volume", "unit": "mL", "category": "RV Function", "normal": "35 - 90 mL"},
    "RV_SV": {"description": "Right Ventricle Stroke Volume", "unit": "mL", "category": "RV Function", "normal": "60 - 110 mL"},
    "RV_EF": {"description": "Right Ventricle Ejection Fraction", "unit": "%", "category": "RV Function", "normal": "45 - 65 %"},
    "LV_EDVi": {"description": "LV EDV indexed to BSA", "unit": "mL/m²", "category": "BSA-Indexed", "normal": "60 - 100 mL/m²"},
    "LV_ESVi": {"description": "LV ESV indexed to BSA", "unit": "mL/m²", "category": "BSA-Indexed", "normal": "18 - 40 mL/m²"},
    "LVMi": {"description": "LV Mass indexed to BSA", "unit": "g/m²", "category": "BSA-Indexed", "normal": "50 - 90 g/m²"},
    "RV_EDVi": {"description": "RV EDV indexed to BSA", "unit": "mL/m²", "category": "BSA-Indexed", "normal": "60 - 110 mL/m²"},
    "concentricity": {"description": "LV Concentricity (LVM / LV_EDV)", "unit": "g/mL", "category": "Geometry & Ratios", "normal": "0.7 - 1.1 g/mL"},
    "RV_LV_EDV": {"description": "Ratio RV EDV to LV EDV", "unit": "ratio", "category": "Geometry & Ratios", "normal": "0.9 - 1.2"},
    "ESV_EDV": {"description": "Ratio LV ESV to LV EDV", "unit": "ratio", "category": "Geometry & Ratios", "normal": "0.25 - 0.45"},
    "RVEF_LVEF": {"description": "Ratio RV EF to LV EF", "unit": "ratio", "category": "Geometry & Ratios", "normal": "0.8 - 1.1"},
    "myo_lv_ratio": {"description": "Myocardium to LV Volume Ratio", "unit": "ratio", "category": "Geometry & Ratios", "normal": "0.7 - 1.1"},
    "wt_mean": {"description": "Mean Myocardial Wall Thickness", "unit": "mm", "category": "Wall Thickness", "normal": "6.0 - 10.0 mm"},
    "wt_max": {"description": "Max Myocardial Wall Thickness", "unit": "mm", "category": "Wall Thickness", "normal": "< 12.0 mm"},
    "wt_std": {"description": "Std of Myocardial Wall Thickness", "unit": "mm", "category": "Wall Thickness", "normal": "< 3.0 mm"},
}

CLASS_DESCRIPTIONS = {
    "NOR": "Normal cardiac anatomy and ventricular function within physiological ranges.",
    "DCM": "Dilated Cardiomyopathy: Ventricular enlargement with reduced ejection fraction (LVEF < 40%).",
    "HCM": "Hypertrophic Cardiomyopathy: Pathological myocardial wall thickening (> 15 mm) and increased mass.",
    "MINF": "Myocardial Infarction: Prior ischemic injury with regional wall hypokinesia/akinesia and reduced ejection fraction.",
    "RV": "Abnormal Right Ventricle: Primary right ventricular dilation or systolic dysfunction (RVEF < 40%)."
}

CLASS_FULL_NAMES = {
    "NOR": "Normal",
    "DCM": "Dilated Cardiomyopathy",
    "HCM": "Hypertrophic Cardiomyopathy",
    "MINF": "Myocardial Infarction",
    "RV": "Abnormal Right Ventricle"
}

def numpy_rgb_to_base64_png(rgb_array: np.ndarray) -> str:
    """Encodes RGB numpy array to base64 PNG data URL."""
    bgr = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    success, buffer = cv2.imencode('.png', bgr)
    if not success:
        raise ValueError("Failed to encode image to PNG buffer.")
    return f"data:image/png;base64,{base64.b64encode(buffer).decode('utf-8')}"

def numpy_gray_to_base64_png(gray_slice: np.ndarray) -> str:
    """Encodes normalized grayscale slice to base64 PNG data URL."""
    norm = ((gray_slice - gray_slice.min()) / (gray_slice.max() - gray_slice.min() + 1e-8) * 255).astype(np.uint8)
    success, buffer = cv2.imencode('.png', norm)
    if not success:
        raise ValueError("Failed to encode image to PNG buffer.")
    return f"data:image/png;base64,{base64.b64encode(buffer).decode('utf-8')}"


@app.get("/api/health")
def health():
    """Returns system status, active compute device, and service metadata."""
    models_ready = True
    try:
        # Check if checkpoints exist
        folds_dir = REPO_ROOT / "checkpoints" / "folds_vdino"
        for fold in range(4):
            if not (folds_dir / f"fold_{fold}" / "best_model.pth").exists():
                models_ready = False
                break
    except Exception:
        models_ready = False

    return {
        "status": "healthy",
        "service": "PULSE Cardiac Digital Twin API",
        "device": str(DEVICE),
        "img_size": IMG_SIZE,
        "ensemble_folds": [0, 1, 2, 3],
        "models_ready": models_ready,
        "heart_tabular_ready": HEART_TABULAR_AVAILABLE,
        "supported_formats": [".nii", ".nii.gz"]
    }


@app.get("/api/sample-info")
def get_sample_info():
    """Returns metadata for the bundled Patient 101 sample case."""
    sample_dir = REPO_ROOT.parent / "ACDC" / "database" / "testing" / "patient101"
    available = (sample_dir / "patient101_frame01.nii").exists()
    return {
        "available": available,
        "patient_id": "patient101",
        "ground_truth_class": "DCM",
        "default_height_cm": 169.0,
        "default_weight_kg": 79.0,
        "ed_frame": 1,
        "es_frame": 14,
        "description": "Patient 101: Dilated Cardiomyopathy (DCM) test subject with 4D cine and paired ED/ES frames."
    }


@app.post("/api/analyze")
async def analyze_mri(
    mode: str = Form("paired"),  # "paired", "cine4d", or "sample"
    ed_file: Optional[UploadFile] = File(None),
    es_file: Optional[UploadFile] = File(None),
    cine_file: Optional[UploadFile] = File(None),
    ed_frame_idx: Any = Form(1),
    es_frame_idx: Any = Form(14),
    height_cm: float = Form(170.0),
    weight_kg: float = Form(70.0),
    tta_enabled: bool = Form(True),
    user_confirmed: bool = Form(True)
):
    """
    Executes the 4 core PULSE clinical functions with safe input validation:
      1. Strictly validates NIfTI volumes, masks, shapes, patient IDs, Cine frames before inference
      2. Segments cardiac structures (RV, Myocardium, LV) via 4-fold ensemble
      3. Extracts 23 clinical cardiac biomarkers
      4. Predicts 5-class ACDC diagnosis with probability distribution
      5. Generates high-resolution slice-by-slice base64 overlays for interactive web viewing
    """
    temp_dir = tempfile.TemporaryDirectory()
    try:
        val_res = None
        if mode == "sample":
            # Load local sample patient 101
            sample_dir = REPO_ROOT.parent / "ACDC" / "database" / "testing" / "patient101"
            sample_ed = sample_dir / "patient101_frame01.nii"
            sample_es = sample_dir / "patient101_frame14.nii"
            if not sample_ed.exists() or not sample_es.exists():
                raise HTTPException(status_code=404, detail="Sample files for Patient 101 not found on disk.")
            
            nii_ed = nib.load(str(sample_ed))
            nii_es = nib.load(str(sample_es))
            info_cfg, _ = find_and_parse_info_cfg(sample_ed)
            val_res = validate_pulse_inputs(
                mode="paired",
                ed_nii=nii_ed,
                es_nii=nii_es,
                ed_filename=str(sample_ed),
                es_filename=str(sample_es),
                user_confirmed=True,
                trusted_info_cfg=info_cfg
            )
            # Override height/weight if default
            if height_cm == 170.0 and weight_kg == 70.0:
                height_cm = 169.0
                weight_kg = 79.0

        elif mode == "cine4d":
            if cine_file is None:
                raise HTTPException(status_code=400, detail="4D Cine MRI file is required for cine4d mode.")
            
            cine_ext = ".nii.gz" if cine_file.filename.endswith(".gz") else ".nii"
            cine_path = Path(temp_dir.name) / f"cine{cine_ext}"
            content = await cine_file.read()
            with open(cine_path, "wb") as f:
                f.write(content)
            
            nii_cine = nib.load(str(cine_path))
            info_cfg, _ = find_and_parse_info_cfg(cine_path)
            val_res = validate_pulse_inputs(
                mode="cine4d",
                cine_nii=nii_cine,
                cine_filename=cine_file.filename,
                ed_frame_raw=ed_frame_idx,
                es_frame_raw=es_frame_idx,
                user_confirmed=user_confirmed,
                trusted_info_cfg=info_cfg
            )

        elif mode == "paired":
            if ed_file is None:
                raise HTTPException(status_code=400, detail="Paired mode requires both ED and ES volumes. End-Diastole (ED) volume is missing.")
            if es_file is None:
                raise HTTPException(status_code=400, detail="Paired mode requires both ED and ES volumes. End-Systole (ES) volume is missing.")
            
            ed_ext = ".nii.gz" if ed_file.filename.endswith(".gz") else ".nii"
            ed_path = Path(temp_dir.name) / f"ed{ed_ext}"
            content_ed = await ed_file.read()
            with open(ed_path, "wb") as f:
                f.write(content_ed)
            
            es_ext = ".nii.gz" if es_file.filename.endswith(".gz") else ".nii"
            es_path = Path(temp_dir.name) / f"es{es_ext}"
            content_es = await es_file.read()
            with open(es_path, "wb") as f:
                f.write(content_es)

            nii_ed = nib.load(str(ed_path))
            nii_es = nib.load(str(es_path))
            info_cfg, _ = find_and_parse_info_cfg(ed_path)

            val_res = validate_pulse_inputs(
                mode="paired",
                ed_nii=nii_ed,
                es_nii=nii_es,
                ed_filename=ed_file.filename,
                es_filename=es_file.filename,
                user_confirmed=user_confirmed,
                trusted_info_cfg=info_cfg
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: '{mode}'. Must be 'paired', 'cine4d', or 'sample'.")

        ed_vol = val_res.ed_vol
        es_vol = val_res.es_vol
        zooms = val_res.zooms
        H, W, S = ed_vol.shape

        # Step 2: Segment with cached 4-fold ensemble (Only after all validation passes)
        models = get_models()
        ed_mask = infer_3d_volume(ed_vol, models, tta=tta_enabled)
        es_mask = infer_3d_volume(es_vol, models, tta=tta_enabled)

        # Step 3: Extract 23 biomarkers
        voxvol = float(np.prod(np.abs(zooms))) / 1000.0
        dx, dy = float(zooms[0]), float(zooms[1])
        bsa = bsa_dubois(float(height_cm), float(weight_kg))
        feat = biomarkers(ed_mask, es_mask, voxvol, dx, dy, bsa)

        biomarkers_list = []
        for k in FEAT_KEYS:
            meta = BIOMARKER_META.get(k, {
                "description": k,
                "unit": "",
                "category": "General",
                "normal": "N/A"
            })
            val = round(float(feat.get(k, 0.0)), 2)
            biomarkers_list.append({
                "key": k,
                "description": meta["description"],
                "value": val,
                "unit": meta["unit"],
                "category": meta["category"],
                "normal_range": meta["normal"]
            })

        # Step 4: Diagnosis prediction via Random Forest ensemble
        bundle = get_classifier()
        if bundle is None:
            diagnosis_data = {
                "predicted_class": "UNKNOWN",
                "predicted_full_name": "Classifier Not Found",
                "confidence": 0.0,
                "probabilities": {cls: 0.0 for cls in CLS_NAMES},
                "headline": "⚠️ Diagnosis classifier not saved on disk",
                "details": "checkpoints/diagnosis_classifier.joblib was not found.",
                "description": ""
            }
        else:
            clf = bundle["model"]
            x = np.array([[feat.get(k, 0.0) for k in bundle["feat_keys"]]], float)
            x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
            pred_idx = int(clf.predict(x)[0])
            pred_proba = clf.predict_proba(x)[0]
            pred_name = bundle["cls_names"][pred_idx]
            conf = float(pred_proba[pred_idx])
            
            prob_dict = {
                cname: round(float(p), 4)
                for cname, p in zip(bundle["cls_names"], pred_proba)
            }

            diagnosis_data = {
                "predicted_class": pred_name,
                "predicted_full_name": CLASS_FULL_NAMES.get(pred_name, pred_name),
                "confidence": round(conf * 100, 1),
                "probabilities": prob_dict,
                "headline": f"Predicted Diagnosis: {pred_name} ({CLASS_FULL_NAMES.get(pred_name, pred_name)})",
                "details": f"Biomarker-driven Random Forest ensemble (10 seeds). Voxel spacing: {zooms[0]:.2f} x {zooms[1]:.2f} x {zooms[2]:.2f} mm | Patient BSA: {bsa:.2f} m²",
                "description": CLASS_DESCRIPTIONS.get(pred_name, "")
            }

        # Step 5: Generate base64 PNG overlays for each short-axis slice
        slices_data = []
        for z in range(S):
            ed_overlay_rgb = make_overlay(ed_vol[..., z], ed_mask[..., z])
            es_overlay_rgb = make_overlay(es_vol[..., z], es_mask[..., z])
            
            slices_data.append({
                "slice_index": z + 1,
                "ed_overlay": numpy_rgb_to_base64_png(ed_overlay_rgb),
                "es_overlay": numpy_rgb_to_base64_png(es_overlay_rgb),
                "ed_raw": numpy_gray_to_base64_png(ed_vol[..., z]),
                "es_raw": numpy_gray_to_base64_png(es_vol[..., z]),
            })

        mid_slice = (S // 2) + 1

        return {
            "success": True,
            "metadata": {
                "num_slices": S,
                "mid_slice": mid_slice,
                "dimensions": [int(H), int(W), int(S)],
                "voxel_spacing": [round(float(z), 2) for z in zooms],
                "patient_bsa": round(float(bsa), 2),
                "height_cm": float(height_cm),
                "weight_kg": float(weight_kg),
                "tta_enabled": bool(tta_enabled),
                "patient_id": val_res.patient_id,
                "patient_id_verified": val_res.patient_id_verified,
                "verification_status": val_res.verification_status.value,
                "warnings": val_res.warnings,
            },
            "diagnosis": diagnosis_data,
            "biomarkers": biomarkers_list,
            "slices": slices_data
        }

    except ValidationError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred during volumetric processing.")
    finally:
        temp_dir.cleanup()



# ==============================================================================
# Module II: Tabular Cardiovascular Disease Prediction Endpoints
# ==============================================================================

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


@app.get("/api/heart-tabular/sample")
def get_heart_tabular_sample():
    """Returns the bundled reference sample patient for tabular heart disease prediction."""
    sample_file = HEART_TABULAR_DIR / "examples" / "patient.json"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="Tabular heart disease sample patient file not found.")
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read sample patient: {str(e)}")


@app.post("/api/heart-tabular/predict")
async def predict_heart_disease_tabular(patient: HeartTabularInputModel):
    """
    Executes the independent CDC NHANES Tabular Cardiovascular Disease Model:
      1. Validates all 31 clinical & demographic features against allowed ranges
      2. Runs Stage 1 Anomaly Gate (Isolation Forest) to detect extreme/implausible profiles
      3. Runs Stage 2 Calibrated Logistic Regression classifier (PR-AUC cost-optimal threshold: 0.2003)
      4. Returns structured JSON with risk category, probability, risk factors, and clinical recommendations
    """
    if not HEART_TABULAR_AVAILABLE or HEART_TABULAR_MODEL is None:
        raise HTTPException(
            status_code=503,
            detail="Heart Tabular Prediction Engine is currently unavailable. Please verify model files on server."
        )

    patient_dict = patient.model_dump()

    # --- Strict Input Validation ---
    errors = []

    # Categorical checks
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

    # Numerical physiological range sanity checks
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
        # Run cascade inference using the existing trained model
        pred = predict_heart_tabular(patient_dict, explain=True)
        pred_dict = pred.to_dict(arrays=False)

        # Extract explanation factors cleanly
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


if __name__ == "__main__":
    # Runs on port 8000 so Gradio remains unhindered on 7860
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
