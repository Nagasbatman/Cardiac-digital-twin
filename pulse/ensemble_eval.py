#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULSE-Seg — 5-fold ensemble evaluation + final biomarker diagnosis features.
============================================================================
Loads the 5 trained fold models (pulse_seg.PULSESeg), runs 2.5D + 4-way-TTA
inference on every ACDC patient (train+test), and:

  1. SEGMENTATION (test, full 3D volumes, ED+ES avg):
     - ENSEMBLE: average softmax over the 5 folds -> Dice/IoU/HD95/ASSD per class
     - PER-FOLD: each fold's own test metrics -> mean+/-std (statistical rigor)
  2. DIAGNOSIS FEATURES: biomarkers from the ENSEMBLE predicted masks for all
     150 patients -> JSON consumed by diagnosis_classify.py for the final
     patient-level diagnosis numbers.

Usage:
  python ensemble_eval.py --folds_dir folds --img_size 256 \
         --out diagnosis_features_ensemble.json
"""
import argparse, json, math, warnings
from pathlib import Path
from typing import Dict, List

import numpy as np
import nibabel as nib
import cv2
from scipy import ndimage
import torch
import torch.nn.functional as F

import pulse_seg as PS
from diagnosis_features import (biomarkers, seg_metrics, bsa_dubois,
                                list_patients, zscore, TRAIN_ROOT, TEST_ROOT, CLS_MAP)
from postprocess import postprocess

warnings.filterwarnings("ignore")


def load_folds(folds_dir: Path, img_size: int, device) -> List[torch.nn.Module]:
    models = []
    for fd in sorted(folds_dir.glob("fold_*")):
        if fd.name == "fold_4":
            print("  [skip] fold_4 skipped per user request", flush=True)
            continue
        ck_path = fd / "best_model.pth"
        if not ck_path.exists():
            print(f"  [skip] {fd} has no best_model.pth", flush=True)
            continue

        try:
            print(f"  [load] {fd.name} to GPU ...", flush=True)
            m = PS.PULSESeg(img_size=img_size)
            ck = torch.load(ck_path, map_location='cpu')
            state_dict = ck["model"] if "model" in ck else ck
            renamed_state_dict = {}
            for key, value in state_dict.items():
                key = key.replace(".attention.attention.query.", ".attention.q_proj.")
                key = key.replace(".attention.attention.key.", ".attention.k_proj.")
                key = key.replace(".attention.attention.value.", ".attention.v_proj.")
                key = key.replace(".attention.output.dense.", ".attention.o_proj.")
                renamed_state_dict[key] = value
            m.load_state_dict(renamed_state_dict)
            m.to(device).eval()
            models.append(m)
            print(f"  loaded {ck_path} (fold={ck.get('fold')}, best_dice={ck.get('best_dice'):.4f}) [GPU]", flush=True)
        except Exception as e:
            print(f"  [ERROR] loading {ck_path}: {e}", flush=True)
            raise

    if not models:
        raise RuntimeError("No fold checkpoints found")
    return models


@torch.no_grad()
def infer_volume_ensemble(models, img_path, device, img_size, per_fold=False):
    """2.5D + 4-way TTA, softmax averaged over folds.
    Runs fast batched-slice inference directly on GPU.
    Returns ensemble label map, and optionally a list of per-fold label maps."""
    vol = nib.load(img_path).get_fdata().astype(np.float32)
    H, W, S = vol.shape
    ens = np.zeros((H, W, S), np.uint8)
    pf = [np.zeros((H, W, S), np.uint8) for _ in models] if per_fold else None

    # Pre-process all slices on CPU
    slices_x = []
    for z in range(S):
        z0, z1, z2 = max(z-1, 0), z, min(z+1, S-1)
        sl = [np.ascontiguousarray(zscore(vol[..., zi])) for zi in (z0, z1, z2)]
        r = [cv2.resize(s, (img_size, img_size), interpolation=cv2.INTER_LINEAR) for s in sl]
        slices_x.append(torch.from_numpy(np.stack(r, -1).transpose(2, 0, 1)).float())

    batch_x = torch.stack(slices_x).to(device)  # [S, 3, img_size, img_size]

    fold_probs_all = []  # list of [S, C, img_size, img_size]
    with torch.amp.autocast(device.type):
        for m in models:
            tta_probs = []
            for fh, fv in [(False, False), (True, False), (False, True), (True, True)]:
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

    # Assemble per-slice ensemble predictions
    for z in range(S):
        per_fold_z = [fold_probs_all[mi][z] for mi in range(len(models))]
        ens_prob = torch.stack(per_fold_z).mean(0)
        ens[..., z] = cv2.resize(
            ens_prob.argmax(0).numpy().astype(np.uint8),
            (W, H), interpolation=cv2.INTER_NEAREST)
        if per_fold:
            for i, fpb in enumerate(per_fold_z):
                pf[i][..., z] = cv2.resize(
                    fpb.argmax(0).numpy().astype(np.uint8),
                    (W, H), interpolation=cv2.INTER_NEAREST)

    ens = postprocess(ens)
    if per_fold and pf is not None:
        pf = [postprocess(p) for p in pf]
    return (ens, pf) if per_fold else (ens, None)


def mean_seg(rows_seg: List[Dict]) -> Dict:
    agg = {}
    for name in ("RV", "Myo", "LV"):
        for m in ("dice", "iou", "hd95", "assd"):
            vals = [r[name][m] for r in rows_seg if not np.isnan(r[name][m])]
            agg[(name, m)] = (float(np.mean(vals)), float(np.std(vals))) if vals else (float("nan"), 0.0)
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds_dir", default="folds")
    ap.add_argument("--img_size", type=int, default=256)
    ap.add_argument("--out", default="diagnosis_features_ensemble.json")
    ap.add_argument("--data_root", default=None,
                    help="Path to ACDC database/ dir (contains training/ and testing/)."
                         " Overrides the ACDC_ROOT env var.")
    args = ap.parse_args()

    import diagnosis_features as _df
    if args.data_root:
        _df.TRAIN_ROOT = Path(args.data_root) / "training"
        _df.TEST_ROOT  = Path(args.data_root) / "testing"
    from diagnosis_features import TRAIN_ROOT, TEST_ROOT

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("Loading fold models:")
    models = load_folds(Path(args.folds_dir), args.img_size, device)
    nfold = len(models)

    splits = {"train": list_patients(TRAIN_ROOT), "test": list_patients(TEST_ROOT)}
    tot_pats = sum(len(p) for p in splits.values())
    pidx = 0
    rows = []
    test_ens_seg, test_perfold_seg = [], [[] for _ in range(nfold)]
    for split, pats in splits.items():
        for pid, rec in sorted(pats.items()):
            pidx += 1
            ph = rec["phases"]
            ed_folder, es_folder = ph["ED"]["img"], ph["ES"]["img"]
            # Resolve image and ground‑truth paths (may be a file or a directory containing the .nii/.nii.gz file)
            def resolve_nii(pth):
                p = Path(pth)
                if p.is_file():
                    return str(p)
                if p.is_dir():
                    for f in p.iterdir():
                        if f.suffixes == [".nii", ".gz"] or f.suffix == ".nii":
                            return str(f)
                raise FileNotFoundError(f"NIfTI file not found for {pth}")

            ed_img = resolve_nii(ed_folder)
            es_img = resolve_nii(es_folder)
            gt_ed_path = resolve_nii(ph["ED"]["gt"])
            gt_es_path = resolve_nii(ph["ES"]["gt"])
            zooms = nib.load(ed_img).header.get_zooms()[:3]
            voxvol = float(np.prod(np.abs(zooms))) / 1000.0
            dx, dy = float(zooms[0]), float(zooms[1]); spacing = tuple(float(z) for z in zooms)
            bsa = bsa_dubois(rec["height"], rec["weight"])
            want_pf = (split == "test")
            ed_ens, ed_pf = infer_volume_ensemble(models, ed_img, device, args.img_size, want_pf)
            es_ens, es_pf = infer_volume_ensemble(models, es_img, device, args.img_size, want_pf)
            feat = biomarkers(ed_ens, es_ens, voxvol, dx, dy, bsa)
            gt_ed = nib.load(gt_ed_path).get_fdata().astype(np.int64)
            gt_es = nib.load(gt_es_path).get_fdata().astype(np.int64)
            feat_gt = biomarkers(gt_ed, gt_es, voxvol, dx, dy, bsa)
            row = {"pid": pid, "split": split, "group": rec["group"], "label": CLS_MAP[rec["group"]],
                   "height": rec["height"], "weight": rec["weight"], "bsa": bsa,
                   "feat_pred": feat, "feat_gt": feat_gt}
            if split == "test":
                sm = {n: {m: float(np.nanmean([seg_metrics(ed_ens, gt_ed, spacing)[n][m],
                                               seg_metrics(es_ens, gt_es, spacing)[n][m]]))
                          for m in ("dice", "iou", "hd95", "assd")} for n in ("RV", "Myo", "LV")}
                row["seg"] = sm; test_ens_seg.append(sm)
                for i in range(nfold):
                    smf = {n: {m: float(np.nanmean([seg_metrics(ed_pf[i], gt_ed, spacing)[n][m],
                                                    seg_metrics(es_pf[i], gt_es, spacing)[n][m]]))
                               for m in ("dice", "iou", "hd95", "assd")} for n in ("RV", "Myo", "LV")}
                    test_perfold_seg[i].append(smf)
            rows.append(row)
            print(f"  [{pidx}/{tot_pats}] {split} {pid} done", flush=True)
    Path(args.out).write_text(json.dumps(rows, indent=2))

    # ── Segmentation report ───────────────────────────────────────────────────
    print(f"\n{'='*70}\nENSEMBLE SEGMENTATION (test n={len(test_ens_seg)}, {nfold} folds, 2.5D+TTA)\n{'='*70}")
    ens_agg = mean_seg(test_ens_seg)
    for n in ("RV", "Myo", "LV"):
        print(f"  {n:>3}: Dice {ens_agg[(n,'dice')][0]*100:5.1f}  IoU {ens_agg[(n,'iou')][0]*100:5.1f}"
              f"  HD95 {ens_agg[(n,'hd95')][0]:5.2f}  ASSD {ens_agg[(n,'assd')][0]:5.2f}")
    print(f"  ENSEMBLE Mean Dice: {np.mean([ens_agg[(n,'dice')][0] for n in ('RV','Myo','LV')])*100:.1f}%")

    # per-fold mean dice -> mean+/-std across folds (rigor)
    fold_means = []
    for i in range(nfold):
        fa = mean_seg(test_perfold_seg[i])
        fold_means.append(np.mean([fa[(n,'dice')][0] for n in ('RV','Myo','LV')]))
    print(f"\n  Per-fold mean Dice: {[round(x*100,1) for x in fold_means]}")
    print(f"  Across folds: {np.mean(fold_means)*100:.1f} +/- {np.std(fold_means)*100:.1f}%")
    print(f"\nSaved features -> {args.out}\nRun: diagnosis_classify.py --features {args.out}")


if __name__ == "__main__":
    main()
