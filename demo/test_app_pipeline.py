#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for demo/app.py pipeline functions.
Tests both Paired ED/ES mode and 4D Cine mode with real ACDC data.
"""
import os, sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "demo"))

from app import analyze_cardiac_mri, update_slice

class MockFile:
    def __init__(self, path):
        self.name = str(path)

def test_pipeline():
    sample_dir = Path(r"C:\Users\Harshavardan\cardiac_digital_twin\ACDC\database\testing\patient101")
    ed_path = sample_dir / "patient101_frame01.nii"
    es_path = sample_dir / "patient101_frame14.nii"
    cine_path = sample_dir / "patient101_4d.nii"
    
    print("Testing 1: Paired ED/ES volumes...")
    out_ed, out_es, diag_h, diag_probs, diag_info, df_bio, slider = analyze_cardiac_mri(
        ed_file=MockFile(ed_path),
        es_file=MockFile(es_path),
        cine_4d_file=None,
        ed_frame_idx=1,
        es_frame_idx=14,
        height_cm=167,
        weight_kg=86,
        tta_enabled=True
    )
    
    print(f"ED Overlay shape: {out_ed.shape if out_ed is not None else None}")
    print(f"ES Overlay shape: {out_es.shape if out_es is not None else None}")
    print(f"Diagnosis Headline: {diag_h}")
    print(f"Diagnosis Probabilities: {diag_probs}")
    print(f"Biomarkers extracted: {len(df_bio)} rows")
    assert len(df_bio) == 23, f"Expected 23 biomarkers, got {len(df_bio)}"
    print("Test 1 Passed!\n")
    
    print("Testing 2: Interactive slice slider callback...")
    s_ed, s_es = update_slice(5)
    assert s_ed is not None and s_es is not None
    print(f"Slice 5 rendered: {s_ed.shape}, {s_es.shape}")
    print("Test 2 Passed!\n")
    
    print("Testing 3: 4D Cine MRI mode...")
    out_ed4, out_es4, diag_h4, diag_probs4, diag_info4, df_bio4, slider4 = analyze_cardiac_mri(
        ed_file=None,
        es_file=None,
        cine_4d_file=MockFile(cine_path),
        ed_frame_idx=1,
        es_frame_idx=14,
        height_cm=167,
        weight_kg=86,
        tta_enabled=False  # fast test without TTA
    )
    print(f"4D Cine Headline: {diag_h4}")
    assert len(df_bio4) == 23
    print("Test 3 Passed!\n")
    
    print("ALL TESTS PASSED! demo/app.py is fully operational.")

if __name__ == "__main__":
    test_pipeline()
