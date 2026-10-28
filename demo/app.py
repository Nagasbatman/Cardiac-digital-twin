#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULSE — Cardiac MRI Segmentation & Diagnosis Demo
=================================================
Scope strictly limited to four core functions:
  1. Upload a supported 3D/4D cardiac MRI in NIfTI format (.nii / .nii.gz).
  2. Segment cardiac structures (RV, Myocardium, LV) using existing pretrained PULSE checkpoints (folds 0-3).
  3. Extract and display the 23 clinical biomarkers.
  4. Predict one of the 5 ACDC classes: NOR, DCM, HCM, MINF, RV.
"""
import os
import sys
from pathlib import Path

# Add project root and pulse directory to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "pulse"))

import numpy as np
import nibabel as nib
import cv2
import torch
import torch.nn.functional as F
import joblib
import pandas as pd
import gradio as gr

import pulse_seg as PS
from postprocess import postprocess
from diagnosis_features import biomarkers, bsa_dubois, FEAT_KEYS, CLS_NAMES

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 256
COLORS = {1: (220, 40, 40), 2: (40, 200, 60), 3: (50, 90, 230)}  # RV=Red, Myo=Green, LV=Blue
LABELS = {1: "RV", 2: "Myocardium", 3: "LV"}

_MODELS = None
_CLASSIFIER_BUNDLE = None


def get_models():
    """Load local 4-fold models (folds 0-3, skipping fold 4) onto DEVICE once."""
    global _MODELS
    if _MODELS is None:
        models = []
        folds_dir = repo_root / "checkpoints" / "folds_vdino"
        for fold in range(4):
            ckpt = folds_dir / f"fold_{fold}" / "best_model.pth"
            if not ckpt.exists():
                raise FileNotFoundError(f"Missing fold checkpoint: {ckpt}")
            m = PS.PULSESeg(img_size=IMG_SIZE)
            sd = torch.load(ckpt, map_location="cpu")
            state_dict = sd["model"] if "model" in sd else sd
            renamed = {}
            for k, v in state_dict.items():
                k = k.replace(".attention.attention.query.", ".attention.q_proj.")
                k = k.replace(".attention.attention.key.", ".attention.k_proj.")
                k = k.replace(".attention.attention.value.", ".attention.v_proj.")
                k = k.replace(".attention.output.dense.", ".attention.o_proj.")
                renamed[k] = v
            m.load_state_dict(renamed)
            m.to(DEVICE).eval()
            models.append(m)
        _MODELS = models
    return _MODELS


def get_classifier():
    """Load the saved diagnosis classifier bundle if it exists on disk."""
    global _CLASSIFIER_BUNDLE
    if _CLASSIFIER_BUNDLE is None:
        clf_path = repo_root / "checkpoints" / "diagnosis_classifier.joblib"
        if clf_path.exists():
            _CLASSIFIER_BUNDLE = joblib.load(clf_path)
        else:
            _CLASSIFIER_BUNDLE = None
    return _CLASSIFIER_BUNDLE


def zscore(a):
    return (a - a.mean()) / (a.std() + 1e-8)


@torch.no_grad()
def infer_3d_volume(vol, models, tta=True):
    """Batched slice inference with 4-way TTA on GPU across active folds."""
    H, W, S = vol.shape
    ens = np.zeros((H, W, S), np.uint8)

    slices_x = []
    for z in range(S):
        z0, z1, z2 = max(z - 1, 0), z, min(z + 1, S - 1)
        sl = [np.ascontiguousarray(zscore(vol[..., zi])) for zi in (z0, z1, z2)]
        r = [cv2.resize(s, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR) for s in sl]
        slices_x.append(torch.from_numpy(np.stack(r, -1).transpose(2, 0, 1)).float())

    batch_x = torch.stack(slices_x).to(DEVICE)
    flips = [(False, False), (True, False), (False, True), (True, True)] if tta else [(False, False)]

    fold_probs_all = []
    with torch.amp.autocast(DEVICE.type):
        for m in models:
            tta_probs = []
            for fh, fv in flips:
                xi = batch_x
                if fh: xi = xi.flip(-1)
                if fv: xi = xi.flip(-2)
                out = m(xi)
                main = out[0] if isinstance(out, tuple) else out
                sp = F.softmax(main, 1)
                if fh: sp = sp.flip(-1)
                if fv: sp = sp.flip(-2)
                tta_probs.append(sp)
            fold_probs_all.append(torch.stack(tta_probs).mean(0).cpu())

    for z in range(S):
        per_fold_z = [fold_probs_all[mi][z] for mi in range(len(models))]
        ens_prob = torch.stack(per_fold_z).mean(0)
        ens[..., z] = cv2.resize(
            ens_prob.argmax(0).numpy().astype(np.uint8),
            (W, H), interpolation=cv2.INTER_NEAREST
        )

    return postprocess(ens)


def make_overlay(gray_slice, mask_slice):
    """Produce RGB overlay of gray slice with RV (red), Myo (green), LV (blue)."""
    norm = ((gray_slice - gray_slice.min()) / (gray_slice.max() - gray_slice.min() + 1e-8) * 255).astype(np.uint8)
    rgb = cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)
    overlay = rgb.copy()

    # BGR colors for opencv
    color_map = {1: (220, 40, 40), 2: (40, 200, 60), 3: (50, 90, 230)}
    for lab, col in color_map.items():
        m = (mask_slice == lab)
        if m.any():
            overlay[m] = (0.5 * rgb[m] + 0.5 * np.array(col)).astype(np.uint8)
            contours, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, col, 1)
    return overlay


# App state to hold cached volumes for interactive slice browsing
_CACHE = {
    "ed_vol": None, "ed_mask": None,
    "es_vol": None, "es_mask": None,
    "max_slices": 1
}


def analyze_cardiac_mri(ed_file, es_file, cine_4d_file, ed_frame_idx, es_frame_idx, height_cm, weight_kg, tta_enabled):
    """
    Executes the 4 core functions:
      1. Upload & load 3D/4D NIfTI
      2. Segment cardiac structures with PULSE ensemble
      3. Extract 23 clinical biomarkers
      4. Predict ACDC diagnosis class (NOR, DCM, HCM, MINF, RV)
    """
    global _CACHE

    # --- 1. Load NIfTI Image(s) ---
    if cine_4d_file is not None:
        nii = nib.load(cine_4d_file.name)
        data = nii.get_fdata().astype(np.float32)
        if data.ndim != 4:
            return (None, None, None, None, f"Error: Selected 4D Cine MRI but file has shape {data.shape} (ndim={data.ndim}).", None, None)
        T = data.shape[3]
        f_ed = max(0, min(int(ed_frame_idx) - 1, T - 1))
        f_es = max(0, min(int(es_frame_idx) - 1, T - 1))
        ed_vol = data[..., f_ed]
        es_vol = data[..., f_es]
        zooms = nii.header.get_zooms()[:3]
    elif ed_file is not None and es_file is not None:
        nii_ed = nib.load(ed_file.name)
        nii_es = nib.load(es_file.name)
        ed_vol = nii_ed.get_fdata().astype(np.float32)
        es_vol = nii_es.get_fdata().astype(np.float32)
        if ed_vol.ndim == 4: ed_vol = ed_vol[..., 0]
        if es_vol.ndim == 4: es_vol = es_vol[..., 0]
        zooms = nii_ed.header.get_zooms()[:3]
    elif ed_file is not None and es_file is None:
        # Single 3D volume provided
        nii_ed = nib.load(ed_file.name)
        ed_vol = nii_ed.get_fdata().astype(np.float32)
        if ed_vol.ndim == 4: ed_vol = ed_vol[..., 0]
        es_vol = ed_vol.copy()
        zooms = nii_ed.header.get_zooms()[:3]
    else:
        return (None, None, None, None, "Please upload either a 4D Cine MRI file OR paired ED/ES 3D volumes.", None, None)

    if ed_vol.shape != es_vol.shape:
        return (None, None, None, None, f"Spatial mismatch: ED shape {ed_vol.shape} != ES shape {es_vol.shape}.", None, None)

    # --- 2. Segment Cardiac Structures ---
    models = get_models()
    ed_mask = infer_3d_volume(ed_vol, models, tta=tta_enabled)
    es_mask = infer_3d_volume(es_vol, models, tta=tta_enabled)

    _CACHE["ed_vol"] = ed_vol
    _CACHE["ed_mask"] = ed_mask
    _CACHE["es_vol"] = es_vol
    _CACHE["es_mask"] = es_mask
    _CACHE["max_slices"] = ed_vol.shape[2]

    # Render mid-ventricular slice for initial view
    mid_s = ed_vol.shape[2] // 2
    ed_view = make_overlay(ed_vol[..., mid_s], ed_mask[..., mid_s])
    es_view = make_overlay(es_vol[..., mid_s], es_mask[..., mid_s])

    # --- 3. Extract 23 Biomarkers ---
    voxvol = float(np.prod(np.abs(zooms))) / 1000.0
    dx, dy = float(zooms[0]), float(zooms[1])
    bsa = bsa_dubois(float(height_cm), float(weight_kg))
    feat = biomarkers(ed_mask, es_mask, voxvol, dx, dy, bsa)

    # Organize 23 biomarkers into a clean structured table
    biomarker_rows = []
    descriptions = {
        "LV_EDV": ("Left Ventricle End-Diastolic Volume", "mL"),
        "LV_ESV": ("Left Ventricle End-Systolic Volume", "mL"),
        "LV_SV": ("Left Ventricle Stroke Volume", "mL"),
        "LV_EF": ("Left Ventricle Ejection Fraction", "%"),
        "LVM": ("Left Ventricular Myocardial Mass", "g"),
        "Myo_ED": ("Myocardium Volume at ED", "mL"),
        "Myo_ES": ("Myocardium Volume at ES", "mL"),
        "RV_EDV": ("Right Ventricle End-Diastolic Volume", "mL"),
        "RV_ESV": ("Right Ventricle End-Systolic Volume", "mL"),
        "RV_SV": ("Right Ventricle Stroke Volume", "mL"),
        "RV_EF": ("Right Ventricle Ejection Fraction", "%"),
        "LV_EDVi": ("LV EDV indexed to BSA", "mL/m²"),
        "LV_ESVi": ("LV ESV indexed to BSA", "mL/m²"),
        "LVMi": ("LV Mass indexed to BSA", "g/m²"),
        "RV_EDVi": ("RV EDV indexed to BSA", "mL/m²"),
        "concentricity": ("LV Concentricity (LVM / LV_EDV)", "g/mL"),
        "RV_LV_EDV": ("Ratio RV EDV to LV EDV", "ratio"),
        "ESV_EDV": ("Ratio LV ESV to LV EDV", "ratio"),
        "RVEF_LVEF": ("Ratio RV EF to LV EF", "ratio"),
        "myo_lv_ratio": ("Myocardium to LV Volume Ratio", "ratio"),
        "wt_mean": ("Mean Myocardial Wall Thickness", "mm"),
        "wt_max": ("Max Myocardial Wall Thickness", "mm"),
        "wt_std": ("Std of Myocardial Wall Thickness", "mm"),
    }

    for k in FEAT_KEYS:
        desc, unit = descriptions.get(k, (k, ""))
        val = feat.get(k, 0.0)
        biomarker_rows.append({
            "Biomarker": k,
            "Description": desc,
            "Value": round(val, 2),
            "Unit": unit
        })
    df_biomarkers = pd.DataFrame(biomarker_rows)

    # --- 4. Predict ACDC Diagnosis Class ---
    bundle = get_classifier()
    if bundle is None:
        diag_headline = "⚠️ Classifier not saved on disk"
        diag_probs = {"NOR": 0.0, "DCM": 0.0, "HCM": 0.0, "MINF": 0.0, "RV": 0.0}
        diag_details = (
            "The diagnosis classifier bundle ('checkpoints/diagnosis_classifier.joblib') was not found on disk.\n"
            "Please run 'python pulse/save_diagnosis_classifier.py' to fit and save the classifier on training features."
        )
    else:
        clf = bundle["model"]
        x = np.array([[feat.get(k, 0.0) for k in bundle["feat_keys"]]], float)
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        pred_idx = int(clf.predict(x)[0])
        pred_proba = clf.predict_proba(x)[0]
        pred_name = bundle["cls_names"][pred_idx]
        diag_headline = f"Predicted Diagnosis: {pred_name} (Confidence: {pred_proba[pred_idx]*100:.1f}%)"
        diag_probs = {cname: float(p) for cname, p in zip(bundle["cls_names"], pred_proba)}
        diag_details = (
            f"Classification performed via 10-seed ensemble on 23 extracted biomarkers.\n"
            f"Voxel Spacing: {zooms[0]:.2f} x {zooms[1]:.2f} x {zooms[2]:.2f} mm | Patient BSA: {bsa:.2f} m²"
        )

    slider_update = gr.update(maximum=ed_vol.shape[2], value=mid_s + 1, visible=True)
    return ed_view, es_view, diag_headline, diag_probs, diag_details, df_biomarkers, slider_update


def update_slice(slice_num):
    """Interactive slice slider callback."""
    global _CACHE
    if _CACHE["ed_vol"] is None or _CACHE["es_vol"] is None:
        return None, None
    s_idx = max(0, min(int(slice_num) - 1, _CACHE["max_slices"] - 1))
    ed_s = make_overlay(_CACHE["ed_vol"][..., s_idx], _CACHE["ed_mask"][..., s_idx])
    es_s = make_overlay(_CACHE["es_vol"][..., s_idx], _CACHE["es_mask"][..., s_idx])
    return ed_s, es_s


# --- Gradio User Interface ---
TITLE = "PULSE: Cardiac MRI Segmentation & Diagnosis"
SUBTITLE = "Pretrained 4-Fold Ensemble Segmentation & Clinical Biomarker Diagnosis"

with gr.Blocks(title=TITLE, theme=gr.themes.Soft(primary_hue="blue")) as demo:
    gr.Markdown(f"# {TITLE}\n### {SUBTITLE}")
    gr.Markdown(
        "This tool implements four core functions:\n"
        "1. **Upload 3D/4D Cardiac MRI** (.nii / .nii.gz)\n"
        "2. **Segment Cardiac Structures** (RV = Red, Myocardium = Green, LV = Blue)\n"
        "3. **Extract 23 Clinical Biomarkers** (Volumes, EF, Mass, Wall Thickness, Concentricity)\n"
        "4. **Predict ACDC Diagnosis Class** (NOR, DCM, HCM, MINF, RV)"
    )

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Tab("Paired ED & ES Volumes (Recommended)"):
                ed_input = gr.File(label="End-Diastole (ED) Volume (.nii / .nii.gz)", file_types=[".nii", ".gz"])
                es_input = gr.File(label="End-Systole (ES) Volume (.nii / .nii.gz)", file_types=[".nii", ".gz"])

            with gr.Tab("4D Cine MRI"):
                cine_input = gr.File(label="4D Cine Cardiac MRI (.nii / .nii.gz)", file_types=[".nii", ".gz"])
                with gr.Row():
                    ed_frame = gr.Number(label="ED Frame Index", value=1, precision=0)
                    es_frame = gr.Number(label="ES Frame Index", value=10, precision=0)

            with gr.Accordion("Patient Demographics (for BSA Indexing)", open=False):
                with gr.Row():
                    height = gr.Number(label="Height (cm)", value=170)
                    weight = gr.Number(label="Weight (kg)", value=70)

            tta_cb = gr.Checkbox(label="Test-Time Augmentation (4-way flip TTA)", value=True)
            analyze_btn = gr.Button("Run PULSE Analysis", variant="primary", size="lg")

        with gr.Column(scale=2):
            diag_heading = gr.Markdown("### Diagnosis: Ready for analysis")
            diag_chart = gr.Label(label="Diagnosis Class Probabilities (ACDC 5 Classes)")
            diag_info = gr.Textbox(label="Analysis Details", lines=2, interactive=False)

            with gr.Row():
                out_ed = gr.Image(label="End-Diastole (ED) Overlay", height=320)
                out_es = gr.Image(label="End-Systole (ES) Overlay", height=320)

            slice_slider = gr.Slider(minimum=1, maximum=15, step=1, value=1, label="Slice Navigation (Base to Apex)", visible=False)

    with gr.Accordion("23 Extracted Clinical Biomarkers", open=True):
        biomarker_table = gr.DataFrame(
            headers=["Biomarker", "Description", "Value", "Unit"],
            datatype=["str", "str", "number", "str"],
            interactive=False,
            label="Clinical Cardiac Biomarkers Table"
        )

    # Wire event handlers
    analyze_btn.click(
        fn=analyze_cardiac_mri,
        inputs=[ed_input, es_input, cine_input, ed_frame, es_frame, height, weight, tta_cb],
        outputs=[out_ed, out_es, diag_heading, diag_chart, diag_info, biomarker_table, slice_slider]
    )

    slice_slider.change(
        fn=update_slice,
        inputs=[slice_slider],
        outputs=[out_ed, out_es]
    )

    gr.Markdown(
        "---\n"
        "**Cardiac Segmentations:** RV = Red, Myocardium = Green, LV = Blue.\n"
        "**ACDC Classes:** NOR = Normal, DCM = Dilated Cardiomyopathy, HCM = Hypertrophic Cardiomyopathy, MINF = Myocardial Infarction, RV = Abnormal RV.\n"
        "*For research and educational use only; not a certified medical device.*"
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
