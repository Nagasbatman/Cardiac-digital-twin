#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test FastAPI API Server Input Validation directly using TestClient.
"""

import sys
import unittest
from pathlib import Path
import numpy as np
import nibabel as nib
import io

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pulse"))
sys.path.insert(0, str(REPO_ROOT / "demo"))

from fastapi.testclient import TestClient
from api_server import app

class TestApiValidation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_missing_es_in_paired_mode_rejected(self):
        # Only ed_file supplied
        dummy_nii = io.BytesIO(b"fake nifti content")
        res = self.client.post(
            "/api/analyze",
            data={"mode": "paired"},
            files={"ed_file": ("patient101_frame01.nii", dummy_nii, "application/octet-stream")}
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("End-Systole (ES) volume is missing", res.json()["detail"])

    def test_gt_mask_in_paired_mode_rejected(self):
        # Create a small valid NIfTI with gt filename
        affine = np.diag([1.4, 1.4, 10.0, 1.0])
        data = np.random.normal(120, 30, (32, 32, 4)).astype(np.float32)
        nii = nib.Nifti1Image(data, affine)
        
        bio_ed = io.BytesIO()
        nii.to_stream(bio_ed)
        bio_ed.seek(0)
        
        bio_es = io.BytesIO()
        nii.to_stream(bio_es)
        bio_es.seek(0)

        res = self.client.post(
            "/api/analyze",
            data={"mode": "paired"},
            files={
                "ed_file": ("patient101_frame01_gt.nii", bio_ed, "application/octet-stream"),
                "es_file": ("patient101_frame14.nii", bio_es, "application/octet-stream"),
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("ground-truth", res.json()["detail"].lower())

    def test_invalid_cine_indices_rejected(self):
        # 4D volume with only 5 frames, but asking for frame 10
        affine = np.diag([1.4, 1.4, 10.0, 1.0])
        data = np.random.normal(120, 30, (32, 32, 4, 5)).astype(np.float32)
        nii = nib.Nifti1Image(data, affine)
        
        bio_cine = io.BytesIO()
        nii.to_stream(bio_cine)
        bio_cine.seek(0)

        res = self.client.post(
            "/api/analyze",
            data={
                "mode": "cine4d",
                "ed_frame_idx": "1",
                "es_frame_idx": "10", # out of range for 5 frames
            },
            files={
                "cine_file": ("patient101_4d.nii", bio_cine, "application/octet-stream")
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("out of bounds", res.json()["detail"])

    def test_sample_mode_valid(self):
        # Test sample patient 101 mode runs successfully
        res = self.client.post(
            "/api/analyze",
            data={"mode": "sample", "tta_enabled": "false"}
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertTrue(json_data["success"])
        self.assertIn("metadata", json_data)
        self.assertIn("diagnosis", json_data)
        self.assertIn("biomarkers", json_data)
        self.assertEqual(len(json_data["biomarkers"]), 23)

if __name__ == "__main__":
    unittest.main()
