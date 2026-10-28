#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Save the trained diagnosis classifier to disk for deployable inference.
Trains on the 100 official training patients from diagnosis_features_ensemble.json
and saves the model bundle (classifier, FEAT_KEYS, CLS_NAMES, etc.) to checkpoints/.
"""
import sys
from pathlib import Path

# Ensure pulse package is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "pulse"))

import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, classification_report
from diagnosis_features import CLS_NAMES, FEAT_KEYS


def main():
    feat_path = repo_root / "diagnosis_features_ensemble.json"
    if not feat_path.exists():
        raise FileNotFoundError(f"{feat_path} does not exist.")

    with open(feat_path) as f:
        rows = json.load(f)

    # Train split
    tr_rows = [r for r in rows if r["split"] == "train"]
    Xtr = np.array([[r["feat_pred"].get(k, 0.0) for k in FEAT_KEYS] for r in tr_rows], float)
    Xtr = np.nan_to_num(Xtr, nan=0.0, posinf=0.0, neginf=0.0)
    ytr = np.array([r["label"] for r in tr_rows], int)

    # Test split
    te_rows = [r for r in rows if r["split"] == "test"]
    Xte = np.array([[r["feat_pred"].get(k, 0.0) for k in FEAT_KEYS] for r in te_rows], float)
    Xte = np.nan_to_num(Xte, nan=0.0, posinf=0.0, neginf=0.0)
    yte = np.array([r["label"] for r in te_rows], int)

    print(f"Loaded features: {len(Xtr)} train, {len(Xte)} test, {len(FEAT_KEYS)} biomarkers")

    # Fit a 10-seed soft-voting ensemble of RandomForestClassifiers (exactly matching diagnosis_classify.py evaluate())
    estimators = [
        (f"rf_{s}", RandomForestClassifier(
            n_estimators=600, max_depth=None, min_samples_leaf=1,
            random_state=s, class_weight="balanced"
        ))
        for s in range(10)
    ]
    ensemble = VotingClassifier(estimators=estimators, voting="soft")
    ensemble.fit(Xtr, ytr)

    # Test evaluation
    preds = ensemble.predict(Xte)
    test_acc = accuracy_score(yte, preds)
    print(f"\nSaved Classifier Test Accuracy: {test_acc*100:.1f}%")
    print(classification_report(yte, preds, target_names=CLS_NAMES, digits=3))

    out_dir = repo_root / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "diagnosis_classifier.joblib"

    bundle = {
        "model": ensemble,
        "feat_keys": FEAT_KEYS,
        "cls_names": CLS_NAMES,
        "test_acc": test_acc
    }
    joblib.dump(bundle, out_path)
    print(f"Saved classifier bundle to: {out_path}")


if __name__ == "__main__":
    main()
