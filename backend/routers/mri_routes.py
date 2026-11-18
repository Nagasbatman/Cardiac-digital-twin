"""Module I: Cardiovascular MRI Analysis API routes.
"""
from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import nibabel as nib
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

# Resolve paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "pulse") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "pulse"))
if str(REPO_ROOT / "demo") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "demo"))

from app import get_models, get_classifier, infer_3d_volume, make_overlay, DEVICE, IMG_SIZE
from diagnosis_features import biomarkers, bsa_dubois, FEAT_KEYS, CLS_NAMES
from validation import (
    ValidationError,
    validate_pulse_inputs,
    find_and_parse_info_cfg,
    PhaseStatus,
)
import time
from backend.db.persistence import persist_mri_analysis_run

router = APIRouter(tags=["Module I: Cardiac MRI"])

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


@router.get("/api/sample-info")
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


@router.post("/api/analyze")
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
    """Executes cardiac MRI analysis pipeline."""
    t0 = time.time()
    temp_dir = tempfile.TemporaryDirectory()
    try:
        val_res = None
        if mode == "sample":
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
            if ed_file is None and es_file is None:
                raise ValidationError("Paired mode requires both End-Diastole (ED) and End-Systole (ES) volumes. Neither was provided.")
            if ed_file is None:
                raise ValidationError("Paired mode requires both ED and ES volumes. End-Diastole (ED) volume is missing.")
            if es_file is None:
                raise ValidationError("Paired mode requires both ED and ES volumes. End-Systole (ES) volume is missing.")

            ed_ext = ".nii.gz" if ed_file.filename.endswith(".gz") else ".nii"
            es_ext = ".nii.gz" if es_file.filename.endswith(".gz") else ".nii"
            ed_path = Path(temp_dir.name) / f"ed{ed_ext}"
            es_path = Path(temp_dir.name) / f"es{es_ext}"

            with open(ed_path, "wb") as f:
                f.write(await ed_file.read())
            with open(es_path, "wb") as f:
                f.write(await es_file.read())

            try:
                nii_ed = nib.load(str(ed_path))
            except Exception as exc:
                raise ValidationError(f"Invalid End-Diastole (ED) NIfTI file: {exc}")

            try:
                nii_es = nib.load(str(es_path))
            except Exception as exc:
                raise ValidationError(f"Invalid End-Systole (ES) NIfTI file: {exc}")

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
            raise HTTPException(status_code=400, detail=f"Unsupported mode '{mode}'. Choose 'paired', 'cine4d', or 'sample'.")

        models = get_models()
        try:
            bundle = get_classifier()
        except Exception:
            bundle = None

        pred_ed = infer_3d_volume(val_res.ed_vol, models, tta=tta_enabled)
        pred_es = infer_3d_volume(val_res.es_vol, models, tta=tta_enabled)

        voxvol = float(np.prod(np.abs(val_res.zooms))) / 1000.0
        dx, dy = float(val_res.zooms[0]), float(val_res.zooms[1])
        bsa = bsa_dubois(float(height_cm), float(weight_kg))
        feats = biomarkers(pred_ed, pred_es, voxvol, dx, dy, bsa)

        if bundle is not None and "model" in bundle:
            clf = bundle["model"]
            feat_keys = bundle.get("feat_keys", FEAT_KEYS)
            cls_names = bundle.get("cls_names", CLS_NAMES)
            X_cls = np.array([[feats.get(k, 0.0) for k in feat_keys]], float)
            X_cls = np.nan_to_num(X_cls, nan=0.0, posinf=0.0, neginf=0.0)
            proba = clf.predict_proba(X_cls)[0]
            pred_idx = int(np.argmax(proba))
            pred_class = cls_names[pred_idx]
            confidence = float(proba[pred_idx])
            class_probs = {name: round(float(p) * 100, 1) for name, p in zip(cls_names, proba)}
            class_probs_fraction = {name: float(p) for name, p in zip(cls_names, proba)}
        else:
            # Do not fabricate a normal diagnosis when no classifier output
            # exists. The UI renders UNKNOWN and unavailable confidence/probabilities.
            pred_class = "UNKNOWN"
            confidence = None
            class_probs = None
            class_probs_fraction = None

        confidence_percent = round(confidence * 100, 1) if confidence is not None else None
        predicted_full_name = CLASS_FULL_NAMES.get(pred_class)
        diagnosis_data = {
            # Canonical fields consumed by the Module I frontend. Confidence is
            # a percentage; probabilities are fractions in [0, 1].
            "predicted_class": pred_class,
            "predicted_full_name": predicted_full_name,
            "confidence": confidence_percent,
            "probabilities": class_probs_fraction,
            "headline": predicted_full_name,
            "details": None,
            # Keep existing field names for any current API consumers.
            "prediction": pred_class,
            "prediction_full_name": predicted_full_name or pred_class,
            "description": CLASS_DESCRIPTIONS.get(pred_class, ""),
            "confidence_percent": confidence_percent,
            "class_probabilities": class_probs,
        }

        biomarkers_list = []
        for k in FEAT_KEYS:
            meta = BIOMARKER_META.get(k, {})
            val = float(feats.get(k, 0.0))
            biomarkers_list.append({
                "key": k,
                "name": meta.get("description", k),
                "category": meta.get("category", "General"),
                "value": round(val, 2),
                "unit": meta.get("unit", ""),
                "normal_range": meta.get("normal", "N/A"),
            })

        num_slices = val_res.ed_vol.shape[2]
        slices_data = []
        for s in range(num_slices):
            ed_raw = val_res.ed_vol[:, :, s]
            ed_seg = pred_ed[:, :, s]
            es_raw = val_res.es_vol[:, :, s]
            es_seg = pred_es[:, :, s]

            slices_data.append({
                "slice_index": s,
                "ed_raw": numpy_gray_to_base64_png(ed_raw),
                "ed_overlay": numpy_rgb_to_base64_png(make_overlay(ed_raw, ed_seg)),
                "es_raw": numpy_gray_to_base64_png(es_raw),
                "es_overlay": numpy_rgb_to_base64_png(make_overlay(es_raw, es_seg)),
            })

        meta_dict = {
            "num_slices": num_slices,
            "mid_slice": (num_slices // 2) + 1,
            "dimensions": [int(val_res.ed_vol.shape[0]), int(val_res.ed_vol.shape[1]), int(val_res.ed_vol.shape[2])],
            "voxel_spacing": [round(float(val_res.zooms[0]), 2), round(float(val_res.zooms[1]), 2), round(float(val_res.zooms[2]), 2)],
            "patient_bsa": round(bsa, 2),
            "height_cm": float(height_cm),
            "weight_kg": float(weight_kg),
            "tta_enabled": tta_enabled,
            "patient_id": getattr(val_res, "patient_id", None),
            "patient_id_verified": getattr(val_res, "patient_id_verified", False),
            "verification_status": val_res.verification_status.value,
            "warnings": val_res.warnings,
        }

        result_payload = {
            "success": True,
            "metadata": meta_dict,
            "patient_info": {
                "height_cm": float(height_cm),
                "weight_kg": float(weight_kg),
                "bsa": round(bsa, 2),
                "tta_enabled": tta_enabled,
                "verification_status": val_res.verification_status.value,
                "warnings": val_res.warnings,
            },
            "diagnosis": diagnosis_data,
            "biomarkers": biomarkers_list,
            "slices": slices_data,
        }

        # Persist to database in schema pulse (fail-safe)
        try:
            elapsed_ms = (time.time() - t0) * 1000.0 if "t0" in locals() else None
            persist_mri_analysis_run(result_payload, mode=mode, execution_time_ms=elapsed_ms)
        except Exception:
            pass

        return result_payload

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

