#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification script: runs end-to-end inference on a single ACDC patient.
1. Loads 3D ED and ES NIfTI images
2. Performs 4-fold ensemble segmentation
3. Extracts all 23 clinical biomarkers
4. Runs the saved diagnosis classifier
5. Saves visualization slice overlay to disk
"""
import os, sys, json
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "pulse"))

import numpy as np
import nibabel as nib
import cv2
import torch
import joblib

import pulse_seg as PS
from diagnosis_features import biomarkers, bsa_dubois, seg_metrics, list_patients, CLS_MAP, CLS_NAMES, FEAT_KEYS
from ensemble_eval import load_folds, infer_volume_ensemble


def create_overlay(img_slice, seg_slice):
    """
    Produce RGB overlay: RV=Red (1), Myo=Green (2), LV=Blue (3).
    """
    # Normalize MRI slice to 0-255 uint8
    norm = ((img_slice - img_slice.min()) / (img_slice.max() - img_slice.min() + 1e-8) * 255).astype(np.uint8)
    rgb = cv2.cvtColor(norm, cv2.COLOR_GRAY2RGB)
    
    # Overlay colors (BGR for opencv)
    colors = {
        1: (0, 0, 220),    # RV: Red
        2: (0, 200, 40),    # Myo: Green
        3: (230, 90, 50)    # LV: Blue
    }
    
    overlay = rgb.copy()
    for c, col in colors.items():
        mask = (seg_slice == c)
        if mask.any():
            overlay[mask] = (0.5 * rgb[mask] + 0.5 * np.array(col)).astype(np.uint8)
            # Add contour
            contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, col, 1)
            
    return overlay


def main():
    data_root = Path(r"C:\Users\Harshavardan\cardiac_digital_twin\ACDC\database")
    test_root = data_root / "testing"
    patients = list_patients(test_root)
    
    # Select patient101
    pid = "patient101"
    if pid not in patients:
        pid = sorted(patients.keys())[0]
        
    rec = patients[pid]
    print(f"\n=======================================================")
    print(f"PILOT INFERENCE VERIFICATION: {pid} (True diagnosis: {rec['group']})")
    print(f"=======================================================")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 1. Load models
    folds_dir = repo_root / "checkpoints" / "folds_vdino"
    models = load_folds(folds_dir, 256, device)
    print(f"Loaded {len(models)} fold models successfully.")
    
    # Resolve file paths
    def resolve_nii(pth):
        p = Path(pth)
        if p.is_file(): return str(p)
        for f in p.iterdir():
            if f.suffixes == [".nii", ".gz"] or f.suffix == ".nii":
                return str(f)
        raise FileNotFoundError(f"NIfTI not found: {pth}")

    ph = rec["phases"]
    ed_path = resolve_nii(ph["ED"]["img"])
    es_path = resolve_nii(ph["ES"]["img"])
    gt_ed_path = resolve_nii(ph["ED"]["gt"])
    gt_es_path = resolve_nii(ph["ES"]["gt"])
    
    # 2. Run segmentation
    print("\nRunning ensemble 2.5D + 4-way TTA segmentation on ED and ES...")
    ed_ens, _ = infer_volume_ensemble(models, ed_path, device, 256, per_fold=False)
    es_ens, _ = infer_volume_ensemble(models, es_path, device, 256, per_fold=False)
    print("Segmentation complete.")
    
    # 3. Biomarkers
    ed_nii = nib.load(ed_path)
    zooms = ed_nii.header.get_zooms()[:3]
    voxvol = float(np.prod(np.abs(zooms))) / 1000.0
    dx, dy = float(zooms[0]), float(zooms[1])
    spacing = tuple(float(z) for z in zooms)
    bsa = bsa_dubois(rec["height"], rec["weight"])
    
    feat = biomarkers(ed_ens, es_ens, voxvol, dx, dy, bsa)
    print("\n-------------------------------------------------------")
    print(f"EXTRACTED 23 CLINICAL BIOMARKERS ({pid}):")
    print("-------------------------------------------------------")
    for k in FEAT_KEYS:
        val = feat.get(k, 0.0)
        print(f"  {k:15s}: {val:10.2f}")
        
    # Segmentation metrics against ground truth
    gt_ed = nib.load(gt_ed_path).get_fdata().astype(np.int64)
    gt_es = nib.load(gt_es_path).get_fdata().astype(np.int64)
    ed_metrics = seg_metrics(ed_ens, gt_ed, spacing)
    es_metrics = seg_metrics(es_ens, gt_es, spacing)
    print("\n-------------------------------------------------------")
    print("SEGMENTATION ACCURACY (Dice & HD95):")
    print("-------------------------------------------------------")
    for name in ("RV", "Myo", "LV"):
        avg_dice = (ed_metrics[name]["dice"] + es_metrics[name]["dice"]) / 2.0 * 100
        avg_hd95 = (ed_metrics[name]["hd95"] + es_metrics[name]["hd95"]) / 2.0
        print(f"  {name:5s}: Dice = {avg_dice:5.1f}% | HD95 = {avg_hd95:5.2f} mm")
        
    # 4. Predict diagnosis using saved classifier
    clf_path = repo_root / "checkpoints" / "diagnosis_classifier.joblib"
    if not clf_path.exists():
        raise FileNotFoundError(f"Diagnosis classifier not found at {clf_path}")
        
    bundle = joblib.load(clf_path)
    clf = bundle["model"]
    x = np.array([[feat.get(k, 0.0) for k in bundle["feat_keys"]]], float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    pred_idx = int(clf.predict(x)[0])
    pred_proba = clf.predict_proba(x)[0]
    pred_class = bundle["cls_names"][pred_idx]
    
    print("\n-------------------------------------------------------")
    print(f"PREDICTED DIAGNOSIS CLASS:")
    print("-------------------------------------------------------")
    print(f"  True Class:      {rec['group']}")
    print(f"  Predicted Class: {pred_class} (p = {pred_proba[pred_idx]*100:.1f}%)")
    print("  Class Probabilities:")
    for cname, prob in zip(bundle["cls_names"], pred_proba):
        print(f"    {cname:5s}: {prob*100:5.1f}%")
        
    # 5. Save visual overlay
    out_dir = repo_root / "demo" / "output_samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Middle slice
    mid_s = ed_ens.shape[2] // 2
    ed_vol = ed_nii.get_fdata().astype(np.float32)
    es_vol = nib.load(es_path).get_fdata().astype(np.float32)
    
    ed_overlay = create_overlay(ed_vol[..., mid_s], ed_ens[..., mid_s])
    es_overlay = create_overlay(es_vol[..., mid_s], es_ens[..., mid_s])
    
    # Save side-by-side ED and ES
    combined = np.hstack([ed_overlay, es_overlay])
    save_path = out_dir / f"{pid}_ed_es_overlay.png"
    cv2.imwrite(str(save_path), combined)
    print(f"\nSaved segmentation overlay to: {save_path}")
    print("Verification successfully complete!\n")


if __name__ == "__main__":
    main()
