#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULSE Safe Input Validation Test Suite
======================================
Covers all 18 validation criteria from Master Prompt Section 10 using
fast synthetic NIfTI fixtures without requiring GPU or model weights.
"""

import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import nibabel as nib

# Add repo root and pulse directory
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pulse"))
sys.path.insert(0, str(REPO_ROOT / "demo"))

from validation import (
    ValidationError,
    PhaseStatus,
    inspect_is_segmentation_mask,
    extract_patient_id,
    validate_patient_ids,
    validate_spatial_compatibility,
    validate_cine_4d_frames,
    find_and_parse_info_cfg,
    evaluate_phase_verification,
    validate_pulse_inputs,
)


class TestPulseValidation(unittest.TestCase):
    def setUp(self):
        # Create standard synthetic 3D MRI image
        self.affine_standard = np.diag([1.4, 1.4, 10.0, 1.0])
        # Generate continuous grayscale values (like genuine MRI scan)
        np.random.seed(42)
        mri_data = np.random.normal(loc=120.0, scale=35.0, size=(64, 64, 8)).astype(np.float32)
        self.nii_valid_mri = nib.Nifti1Image(mri_data, self.affine_standard)
        self.nii_valid_mri.header.set_zooms((1.4, 1.4, 10.0))

    # 1. Explicitly named _gt.nii and _gt.nii.gz files are rejected
    def test_01_explicit_gt_filename_rejected(self):
        is_mask, _, reason = inspect_is_segmentation_mask(self.nii_valid_mri, "patient001_frame01_gt.nii")
        self.assertTrue(is_mask)
        self.assertIn("ground-truth segmentation mask", reason)

        is_mask_gz, _, _ = inspect_is_segmentation_mask(self.nii_valid_mri, "study_gt.nii.gz")
        self.assertTrue(is_mask_gz)

        with self.assertRaises(ValidationError) as ctx:
            validate_pulse_inputs(
                mode="paired",
                ed_nii=self.nii_valid_mri,
                es_nii=self.nii_valid_mri,
                ed_filename="patient101_frame01_gt.nii",
                es_filename="patient101_frame14.nii"
            )
        self.assertIn("ground-truth", str(ctx.exception).lower())

    # 2. Renamed mask with suspicious/discrete voxel characteristics is rejected
    def test_02_renamed_mask_detected_by_voxels(self):
        # Create discrete segmentation mask (labels 0, 1, 2, 3) with an ordinary scan filename
        mask_data = np.random.choice([0, 1, 2, 3], size=(64, 64, 8), p=[0.7, 0.1, 0.1, 0.1]).astype(np.int16)
        nii_mask = nib.Nifti1Image(mask_data, self.affine_standard)
        
        is_mask, is_susp, reason = inspect_is_segmentation_mask(nii_mask, "ordinary_scan_renamed.nii")
        self.assertTrue(is_mask)
        self.assertIn("discrete integer label values", reason)

        with self.assertRaises(ValidationError) as ctx:
            validate_pulse_inputs(
                mode="paired",
                ed_nii=nii_mask,
                es_nii=self.nii_valid_mri,
                ed_filename="ordinary_scan_renamed.nii",
                es_filename="patient101_es.nii"
            )
        self.assertIn("discrete integer label", str(ctx.exception))

    # 3. Legitimate MRI with unusual intensities is NOT rejected
    def test_03_legitimate_mri_unusual_intensities_accepted(self):
        # Scan with negative values and continuous decimals
        unusual_mri_data = (np.random.rand(64, 64, 8) * 10.0 - 5.0).astype(np.float32)
        nii_unusual = nib.Nifti1Image(unusual_mri_data, self.affine_standard)
        
        is_mask, is_susp, _ = inspect_is_segmentation_mask(nii_unusual, "patient101_ed.nii")
        self.assertFalse(is_mask)
        self.assertFalse(is_susp)

    # 4. Missing ED and missing ES volumes are rejected independently
    def test_04_missing_ed_and_es_rejected_independently(self):
        # Missing both
        with self.assertRaises(ValidationError) as ctx_both:
            validate_pulse_inputs(mode="paired", ed_nii=None, es_nii=None)
        self.assertIn("Neither was provided", str(ctx_both.exception))

        # Missing ED only
        with self.assertRaises(ValidationError) as ctx_ed:
            validate_pulse_inputs(mode="paired", ed_nii=None, es_nii=self.nii_valid_mri)
        self.assertIn("End-Diastole (ED) volume is missing", str(ctx_ed.exception))

        # Missing ES only
        with self.assertRaises(ValidationError) as ctx_es:
            validate_pulse_inputs(mode="paired", ed_nii=self.nii_valid_mri, es_nii=None)
        self.assertIn("End-Systole (ES) volume is missing", str(ctx_es.exception))

    # 5. ED is NEVER silently duplicated as ES
    def test_05_no_silent_duplication_when_es_omitted_or_identical(self):
        # Identical file names
        with self.assertRaises(ValidationError) as ctx_same_name:
            validate_pulse_inputs(
                mode="paired",
                ed_nii=self.nii_valid_mri,
                es_nii=self.nii_valid_mri,
                ed_filename="patient101_frame01.nii",
                es_filename="patient101_frame01.nii"
            )
        self.assertIn("Identical files provided", str(ctx_same_name.exception))

        # Identical voxel data array
        with self.assertRaises(ValidationError) as ctx_same_data:
            validate_pulse_inputs(
                mode="paired",
                ed_nii=self.nii_valid_mri,
                es_nii=self.nii_valid_mri,
                ed_filename="patient101_ed.nii",
                es_filename="patient101_es.nii"
            )
        self.assertIn("identical", str(ctx_same_data.exception).lower())

    # 6. Shape mismatches are rejected
    def test_06_shape_mismatches_rejected(self):
        mri_es_diff_shape = nib.Nifti1Image(
            np.random.normal(120, 30, size=(64, 48, 8)).astype(np.float32),
            self.affine_standard
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_spatial_compatibility(self.nii_valid_mri, mri_es_diff_shape)
        self.assertIn("Spatial dimension mismatch", str(ctx.exception))

    # 7. Conflicting voxel spacing, orientation, or spatial transforms
    def test_07_spatial_conflicts_rejected(self):
        # Spacing conflict
        nii_diff_spacing = nib.Nifti1Image(
            np.random.normal(120, 30, size=(64, 64, 8)).astype(np.float32),
            np.diag([2.5, 2.5, 10.0, 1.0])
        )
        nii_diff_spacing.header.set_zooms((2.5, 2.5, 10.0))
        with self.assertRaises(ValidationError) as ctx_space:
            validate_spatial_compatibility(self.nii_valid_mri, nii_diff_spacing)
        self.assertIn("voxel spacing mismatch", str(ctx_space.exception).lower())

        # Orientation conflict (e.g. flipped axis)
        aff_flipped = np.diag([-1.4, 1.4, 10.0, 1.0])
        nii_flipped_ornt = nib.Nifti1Image(
            np.random.normal(120, 30, size=(64, 64, 8)).astype(np.float32),
            aff_flipped
        )
        nii_flipped_ornt.header.set_zooms((1.4, 1.4, 10.0))
        with self.assertRaises(ValidationError) as ctx_ornt:
            validate_spatial_compatibility(self.nii_valid_mri, nii_flipped_ornt)
        self.assertIn("orientation", str(ctx_ornt.exception).lower())

    # 8. Different identifiable patient IDs are rejected
    def test_08_patient_id_mismatch_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_patient_ids("patient101_frame01.nii", "patient102_frame14.nii")
        self.assertIn("Patient ID mismatch", str(ctx.exception))
        self.assertIn("patient101", str(ctx.exception))
        self.assertIn("patient102", str(ctx.exception))

    # 9. Matching shapes without patient IDs do not prove patient identity
    def test_09_matching_shapes_without_id_does_not_verify_identity(self):
        cand_id, is_verified, notice = validate_patient_ids("ed_scan.nii", "es_scan.nii")
        self.assertFalse(is_verified)
        self.assertIn("could not be independently established", notice)
        self.assertIn("do not prove", notice)

    # 10. Valid integer Cine indices are accepted
    def test_10_valid_integer_cine_indices_accepted(self):
        cine_data = np.random.normal(120, 30, size=(64, 64, 8, 20)).astype(np.float32)
        nii_cine = nib.Nifti1Image(cine_data, self.affine_standard)
        ed_1b, es_1b, ed_0b, es_0b = validate_cine_4d_frames(nii_cine, 1, 14)
        self.assertEqual(ed_1b, 1)
        self.assertEqual(es_1b, 14)
        self.assertEqual(ed_0b, 0)
        self.assertEqual(es_0b, 13)

    # 11. Fractional, negative, missing, and out-of-range Cine indices rejected
    def test_11_invalid_cine_indices_rejected(self):
        cine_data = np.random.normal(120, 30, size=(64, 64, 8, 20)).astype(np.float32)
        nii_cine = nib.Nifti1Image(cine_data, self.affine_standard)

        # Fractional
        with self.assertRaises(ValidationError):
            validate_cine_4d_frames(nii_cine, 1.5, 14)

        # Negative
        with self.assertRaises(ValidationError):
            validate_cine_4d_frames(nii_cine, -1, 14)

        # Out of bounds (> 20)
        with self.assertRaises(ValidationError):
            validate_cine_4d_frames(nii_cine, 1, 25)

        # Missing
        with self.assertRaises(ValidationError):
            validate_cine_4d_frames(nii_cine, None, 14)

        # Identical
        with self.assertRaises(ValidationError):
            validate_cine_4d_frames(nii_cine, 5, 5)

    # 12. Zero-based and one-based frame-number conversions tested explicitly
    def test_12_frame_number_conversions_explicit(self):
        cine_data = np.random.normal(120, 30, size=(64, 64, 8, 10)).astype(np.float32)
        nii_cine = nib.Nifti1Image(cine_data, self.affine_standard)
        # 1-based: ED=1, ES=10 -> 0-based: ED=0, ES=9
        ed_1b, es_1b, ed_0b, es_0b = validate_cine_4d_frames(nii_cine, 1, 10)
        self.assertEqual(ed_0b, ed_1b - 1)
        self.assertEqual(es_0b, es_1b - 1)
        self.assertEqual((ed_0b, es_0b), (0, 9))

    # 13. Expected ED/ES values from valid Info.cfg parsed and compared
    def test_13_info_cfg_parsing_and_matching(self):
        with tempfile.TemporaryDirectory() as td:
            patient_dir = Path(td) / "patient999"
            patient_dir.mkdir()
            cfg_file = patient_dir / "Info.cfg"
            cfg_file.write_text("ED: 1\nES: 12\nHeight: 175.0\nWeight: 75.0\nGroup: NOR\n")
            scan_file = patient_dir / "patient999_4d.nii"
            
            info, err = find_and_parse_info_cfg(scan_file)
            self.assertIsNotNone(info)
            self.assertEqual(info["ED"], 1)
            self.assertEqual(info["ES"], 12)
            self.assertIsNone(err)

    # 14. Incorrect selections produce warnings
    def test_14_selection_differs_from_info_cfg_produces_warning(self):
        info_cfg = {"ED": 1, "ES": 14}
        status, warnings = evaluate_phase_verification(
            info_cfg=info_cfg,
            selected_ed=2,
            selected_es=10,
            user_confirmed=True
        )
        self.assertEqual(status, PhaseStatus.USER_CONFIRMED)
        self.assertTrue(any("Metadata Warning" in w for w in warnings))

    # 15. Missing or malformed metadata is handled safely
    def test_15_malformed_info_cfg_handled_safely(self):
        with tempfile.TemporaryDirectory() as td:
            patient_dir = Path(td) / "patient888"
            patient_dir.mkdir()
            cfg_file = patient_dir / "Info.cfg"
            cfg_file.write_text("Malformed Content Without Colons Or Values\n")
            scan_file = patient_dir / "patient888_4d.nii"

            info, err = find_and_parse_info_cfg(scan_file)
            self.assertIsNone(info)
            self.assertIsNotNone(err)

    # 16. Arbitrary scans require user confirmation
    def test_16_arbitrary_scan_requires_user_confirmation(self):
        # Without Info.cfg and user_confirmed=False -> ValidationError
        with self.assertRaises(ValidationError) as ctx:
            evaluate_phase_verification(
                info_cfg=None,
                selected_ed=1,
                selected_es=14,
                user_confirmed=False
            )
        self.assertIn("Phase Confirmation Required", str(ctx.exception))

        # With user_confirmed=True -> USER_CONFIRMED status
        status, warnings = evaluate_phase_verification(
            info_cfg=None,
            selected_ed=1,
            selected_es=14,
            user_confirmed=True
        )
        self.assertEqual(status, PhaseStatus.USER_CONFIRMED)

    # 17. API rejects invalid inputs before inference begins
    def test_17_api_fast_rejection_before_model_loading(self):
        # An invalid input (e.g. mismatched shapes) fails immediately without calling any neural network
        mri_diff_shape = nib.Nifti1Image(np.random.normal(120, 30, size=(64, 48, 8)).astype(np.float32), self.affine_standard)
        with self.assertRaises(ValidationError):
            validate_pulse_inputs(
                mode="paired",
                ed_nii=self.nii_valid_mri,
                es_nii=mri_diff_shape,
                ed_filename="patient101_ed.nii",
                es_filename="patient101_es.nii"
            )

    # 18. Valid inputs retain backward-compatible behavior
    def test_18_valid_inputs_retain_backward_compatibility(self):
        # Distinct ES data
        mri_es_data = np.random.normal(loc=130.0, scale=30.0, size=(64, 64, 8)).astype(np.float32)
        nii_es_valid = nib.Nifti1Image(mri_es_data, self.affine_standard)
        nii_es_valid.header.set_zooms((1.4, 1.4, 10.0))

        res = validate_pulse_inputs(
            mode="paired",
            ed_nii=self.nii_valid_mri,
            es_nii=nii_es_valid,
            ed_filename="patient101_frame01.nii",
            es_filename="patient101_frame14.nii",
            user_confirmed=True
        )
        self.assertIsNotNone(res.ed_vol)
        self.assertIsNotNone(res.es_vol)
        self.assertEqual(res.ed_vol.shape, (64, 64, 8))
        self.assertEqual(res.es_vol.shape, (64, 64, 8))
        self.assertEqual(res.patient_id, "patient101")
        self.assertTrue(res.patient_id_verified)


if __name__ == "__main__":
    unittest.main()
