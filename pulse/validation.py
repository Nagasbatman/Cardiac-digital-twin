#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PULSE Safe Input Validation Engine
==================================
Deterministic, non-trained input validation rules and error handling for
PULSE Cardiac MRI Segmentation and Diagnosis.

Rules Enforced:
1. Ground-Truth Mask Rejection (filename heuristics, NIfTI header intent, and discrete label distributions).
2. Strict Paired Inputs Requirement (both ED & ES required, zero silent duplication).
3. Spatial Compatibility Validation (dimensions, voxel spacing, orientation axcodes, affine transforms).
4. Patient ID Mismatch Detection (regex extraction, conflict rejection, unverified notices).
5. 4D Cine Frame Selection Validation (4D ndim, integer enforcement, valid range [1, T], distinct phases).
6. Info.cfg Dataset Metadata Integration (expected ED/ES display, warning on mismatch, safe parsing).
7. Confirmation for Arbitrary Scans (distinguishing metadata-verified vs user-confirmed vs unverified).
8. Centralized entry point protection before expensive model inference.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Union
from enum import Enum
import numpy as np
import nibabel as nib


class ValidationError(ValueError):
    """Raised when an uploaded file or parameter fails clinical validation."""
    pass


class PhaseStatus(str, Enum):
    METADATA_VERIFIED = "metadata-verified"
    USER_CONFIRMED = "user-confirmed"
    UNVERIFIED = "unverified"


# ==============================================================================
# 1. Ground-Truth Segmentation Mask Inspection
# ==============================================================================

MASK_FILENAME_PATTERNS = [
    r"_gt\.nii(\.gz)?$",
    r"_dseg\.nii(\.gz)?$",
    r"_mask\.nii(\.gz)?$",
    r"_seg\.nii(\.gz)?$",
    r"ground_?truth",
]

def inspect_is_segmentation_mask(
    nii_obj: nib.Nifti1Image,
    filename: str = ""
) -> Tuple[bool, bool, str]:
    """
    Deterministically inspects whether a NIfTI volume is a ground-truth segmentation mask.
    
    Returns:
        (is_mask, is_suspicious, reason)
        - is_mask: Confident ground-truth mask -> reject with error.
        - is_suspicious: Inconclusive characteristics -> warning/confirmation.
        - reason: Explanation of the determination.
    """
    fname = Path(filename).name.lower() if filename else ""

    # Check 1: Filename patterns
    for pat in MASK_FILENAME_PATTERNS:
        if re.search(pat, fname):
            return (
                True,
                False,
                f"File '{filename}' indicates a ground-truth segmentation mask by name pattern ('{pat}'). "
                f"Ground-truth masks cannot be analyzed as raw MRI scans."
            )

    # Check 2: NIfTI Header intent and description
    hdr = nii_obj.header
    try:
        intent_code = int(hdr.get("intent_code", 0))
    except Exception:
        intent_code = 0

    # NIFTI_INTENT_LABEL = 1002
    if intent_code == 1002:
        return (
            True,
            False,
            f"NIfTI header intent code ({intent_code} = NIFTI_INTENT_LABEL) in '{filename}' "
            f"explicitly identifies this file as a segmentation label map."
        )

    for field in ("descrip", "intent_name", "aux_file"):
        try:
            val = hdr.get(field, b"")
            if isinstance(val, (bytes, np.bytes_)):
                val_str = val.decode("utf-8", errors="ignore").lower()
            else:
                val_str = str(val).lower()
            if any(term in val_str for term in ("segmentation", "ground truth", "label map", "manual contour")):
                return (
                    True,
                    False,
                    f"NIfTI header '{field}' ('{val_str.strip()}') identifies '{filename}' "
                    f"as a segmentation mask."
                )
        except Exception:
            pass

    # Check 3: Voxel value distribution heuristics
    data = nii_obj.get_fdata()
    if data.size > 0:
        # Check if values are all exact integers
        is_integer_valued = np.all(np.isclose(data, np.round(data), atol=1e-5))
        
        if is_integer_valued:
            # Check unique values
            uvals = np.unique(data)
            cardinality = len(uvals)
            max_val = float(np.max(uvals))
            min_val = float(np.min(uvals))

            # Standard cardiac segmentation masks have classes {0=BG, 1=RV, 2=Myo, 3=LV}
            # Or subset thereof (e.g. {0, 1, 2, 3})
            if min_val >= 0 and max_val <= 5 and 1 < cardinality <= 6:
                if set(uvals).issubset({0, 1, 2, 3, 4, 5}):
                    return (
                        True,
                        False,
                        f"File '{filename}' contains discrete integer label values {sorted([int(v) for v in uvals])} "
                        f"strictly within [0..5] (cardinality={cardinality}). This matches a categorical segmentation mask, "
                        f"not a continuous MRI signal intensity distribution."
                    )
            
            # Suspicious but inconclusive (e.g., small integer cardinality <= 15)
            if min_val >= 0 and max_val <= 20 and 1 < cardinality <= 15:
                return (
                    False,
                    True,
                    f"File '{filename}' has an unusually low discrete intensity cardinality ({cardinality} distinct values, max={max_val}). "
                    f"Please verify this is a raw MR acquisition rather than a converted label map."
                )

    # Note: heuristic limitations
    return (False, False, "Intensity distribution consistent with continuous MR signal intensities.")


# ==============================================================================
# 2. Patient ID Extraction & Verification
# ==============================================================================

PATIENT_ID_PATTERNS = [
    r"(patient\d+)",
    r"(pat_?\d+)",
    r"sub-([a-zA-Z0-9]+)",
    r"(case_?\d+)",
]

def extract_patient_id(filename: str) -> Optional[str]:
    """Extracts a patient identifier from a filename using standardized patterns."""
    if not filename:
        return None
    name = Path(filename).name.lower()
    for pat in PATIENT_ID_PATTERNS:
        m = re.search(pat, name)
        if m:
            return m.group(1).lower()
    return None


def validate_patient_ids(
    filename_ed: str,
    filename_es: str
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Compares patient IDs extracted from ED and ES filenames.
    
    Returns:
        (patient_id, is_verified, notice_or_warning)
    """
    id_ed = extract_patient_id(filename_ed)
    id_es = extract_patient_id(filename_es)

    if id_ed and id_es:
        if id_ed != id_es:
            raise ValidationError(
                f"Patient ID mismatch: End-Diastole volume appears to belong to '{id_ed}', "
                f"while End-Systole volume belongs to '{id_es}'. "
                f"Cardiac functional analysis requires paired volumes from the same subject."
            )
        return (id_ed, True, f"Patient ID '{id_ed}' consistently identified across both volumes.")
    
    cand_id = id_ed or id_es
    notice = (
        "Patient identity could not be independently established from available file headers or names. "
        "Matching spatial dimensions and voxel spacing do not prove two volumes belong to the same patient."
    )
    return (cand_id, False, notice)


# ==============================================================================
# 3. Spatial Compatibility Validation
# ==============================================================================

def validate_spatial_compatibility(
    nii_ed: nib.Nifti1Image,
    nii_es: nib.Nifti1Image,
    name_ed: str = "ED",
    name_es: str = "ES"
) -> Tuple[Tuple[float, float, float], List[str]]:
    """
    Validates array dimensions, voxel spacing, canonical orientations, and affine matrices.
    
    Returns:
        (zooms, warnings)
    """
    warnings = []

    # 1. Shape check
    shape_ed = nii_ed.shape[:3]
    shape_es = nii_es.shape[:3]
    if shape_ed != shape_es:
        raise ValidationError(
            f"Spatial dimension mismatch: {name_ed} volume shape {shape_ed} conflicts with "
            f"{name_es} volume shape {shape_es}. Both volumes must have identical 3D dimensions."
        )

    # 2. Voxel spacing check
    zooms_ed = tuple(round(float(z), 3) for z in nii_ed.header.get_zooms()[:3])
    zooms_es = tuple(round(float(z), 3) for z in nii_es.header.get_zooms()[:3])

    if any(z <= 0 for z in zooms_ed) or any(np.isnan(zooms_ed)):
        raise ValidationError(f"Invalid or degenerate voxel spacing in {name_ed} header: {zooms_ed}.")
    if any(z <= 0 for z in zooms_es) or any(np.isnan(zooms_es)):
        raise ValidationError(f"Invalid or degenerate voxel spacing in {name_es} header: {zooms_es}.")

    if not np.allclose(zooms_ed, zooms_es, atol=1e-2):
        raise ValidationError(
            f"Spatial voxel spacing mismatch: {name_ed} spacing {zooms_ed} mm conflicts with "
            f"{name_es} spacing {zooms_es} mm."
        )

    # 3. Canonical orientation check
    try:
        ornt_ed = nib.aff2axcodes(nii_ed.affine)
        ornt_es = nib.aff2axcodes(nii_es.affine)
        if ornt_ed != ornt_es:
            raise ValidationError(
                f"Spatial orientation mismatch: {name_ed} orientation {ornt_ed} conflicts with "
                f"{name_es} orientation {ornt_es}."
            )
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        warnings.append(f"Could not compute canonical orientation codes: {exc}")

    # 4. Affine matrix rotation/scaling check
    aff_ed = nii_ed.affine
    aff_es = nii_es.affine
    # Rotation and scaling components
    if not np.allclose(aff_ed[:3, :3], aff_es[:3, :3], atol=1e-1):
        raise ValidationError(
            f"Spatial affine transform conflict: {name_ed} affine rotation/scaling matrix conflicts with {name_es}."
        )

    # Check translation (origin) difference
    if not np.allclose(aff_ed[:3, 3], aff_es[:3, 3], atol=5.0):
        warnings.append(
            f"Spatial origin offset: {name_ed} origin {tuple(np.round(aff_ed[:3, 3], 1))} differs from "
            f"{name_es} origin {tuple(np.round(aff_es[:3, 3], 1))}. (Common in clinical repositioning)."
        )

    return (zooms_ed, warnings)


# ==============================================================================
# 4. 4D Cine Frame Selection Validation
# ==============================================================================

def validate_cine_4d_frames(
    nii_cine: nib.Nifti1Image,
    ed_frame_raw: Any,
    es_frame_raw: Any,
    filename: str = "cine_4d"
) -> Tuple[int, int, int, int]:
    """
    Validates 4D Cine dimensions and frame indices.
    
    Returns:
        (ed_1based, es_1based, ed_0based, es_0based)
    """
    shape = nii_cine.shape
    if len(shape) != 4:
        raise ValidationError(
            f"Expected a 4D temporal Cine MRI volume, but '{filename}' has {len(shape)} dimensions "
            f"(shape: {shape})."
        )
    
    T = shape[3]
    if T < 2:
        raise ValidationError(
            f"4D Cine MRI study in '{filename}' has only {T} temporal frame(s). "
            f"At least 2 frames (ED and ES) are required for functional ventricular evaluation."
        )

    if ed_frame_raw is None or es_frame_raw is None:
        raise ValidationError("Both ED Frame Index and ES Frame Index are required.")

    # Strict integer validation
    try:
        # Reject fractional floats (e.g. 1.5)
        if isinstance(ed_frame_raw, float) and not ed_frame_raw.is_integer():
            raise ValueError()
        if isinstance(es_frame_raw, float) and not es_frame_raw.is_integer():
            raise ValueError()
        # Reject string representations with non-zero decimals (e.g. "1.5")
        if isinstance(ed_frame_raw, str) and "." in ed_frame_raw:
            if float(ed_frame_raw) != int(float(ed_frame_raw)):
                raise ValueError()
        if isinstance(es_frame_raw, str) and "." in es_frame_raw:
            if float(es_frame_raw) != int(float(es_frame_raw)):
                raise ValueError()
        
        ed_1based = int(ed_frame_raw)
        es_1based = int(es_frame_raw)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Frame indices must be integer values. Received ED='{ed_frame_raw}', ES='{es_frame_raw}'. "
            f"Fractional, empty, or non-numeric inputs are not permitted."
        )

    # Range checks (1-based convention)
    if ed_1based < 1 or ed_1based > T:
        raise ValidationError(
            f"ED frame index {ed_1based} is out of bounds. "
            f"Valid 1-based frame range for this 4D Cine scan is [1, {T}]."
        )
    if es_1based < 1 or es_1based > T:
        raise ValidationError(
            f"ES frame index {es_1based} is out of bounds. "
            f"Valid 1-based frame range for this 4D Cine scan is [1, {T}]."
        )

    # Distinct phases check
    if ed_1based == es_1based:
        raise ValidationError(
            f"ED and ES frame indices cannot be identical (both set to frame {ed_1based}). "
            f"End-diastole (max volume) and end-systole (min volume) must represent distinct cardiac phases."
        )

    # Single, explicit conversion to 0-based internal indexing
    ed_0based = ed_1based - 1
    es_0based = es_1based - 1

    return (ed_1based, es_1based, ed_0based, es_0based)


# ==============================================================================
# 5. Dataset Info.cfg Metadata Reader
# ==============================================================================

def find_and_parse_info_cfg(source_path: Optional[Union[str, Path]]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Safely searches for and parses Info.cfg if the file belongs to an authentic ACDC dataset patient folder.
    
    Returns:
        (info_dict, notice_or_warning)
    """
    if source_path is None:
        return (None, None)

    p = Path(source_path).resolve()
    # Search in directory or parent
    cand_dirs = [p.parent]
    if p.parent.parent.exists():
        cand_dirs.append(p.parent.parent)

    for c_dir in cand_dirs:
        cfg_path = c_dir / "Info.cfg"
        if cfg_path.exists() and cfg_path.is_file():
            # Check reliable association: patient ID in dirname or filename
            dir_name = c_dir.name.lower()
            file_name = p.name.lower()
            m_dir = re.search(r"patient(\d+)", dir_name)
            m_file = re.search(r"patient(\d+)", file_name)

            if m_dir or m_file:
                # Reliably associated
                try:
                    data: Dict[str, Any] = {}
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#") or ":" not in line:
                                continue
                            k, v = line.split(":", 1)
                            k = k.strip()
                            v = v.strip()
                            if k in ("ED", "ES", "NbFrame"):
                                data[k] = int(v)
                            elif k in ("Height", "Weight"):
                                data[k] = float(v)
                            else:
                                data[k] = v
                    
                    if "ED" in data and "ES" in data:
                        return (data, None)
                    else:
                        return (None, f"Info.cfg found in '{c_dir.name}' but missing required ED/ES keys.")
                except Exception as exc:
                    return (None, f"Found Info.cfg in '{c_dir.name}' but failed to parse: {exc}")

    return (None, None)


# ==============================================================================
# 6. User Confirmation & Verification Status
# ==============================================================================

def evaluate_phase_verification(
    info_cfg: Optional[Dict[str, Any]],
    selected_ed: int,
    selected_es: int,
    user_confirmed: bool
) -> Tuple[PhaseStatus, List[str]]:
    """
    Determines phase verification status:
      - METADATA_VERIFIED: matches trusted Info.cfg
      - USER_CONFIRMED: user explicitly confirmed arbitrary scan
      - UNVERIFIED: arbitrary scan and user has not confirmed
    """
    warnings: List[str] = []

    if info_cfg and "ED" in info_cfg and "ES" in info_cfg:
        exp_ed = info_cfg["ED"]
        exp_es = info_cfg["ES"]

        if selected_ed == exp_ed and selected_es == exp_es:
            return (PhaseStatus.METADATA_VERIFIED, warnings)
        else:
            warnings.append(
                f"Metadata Warning: Selected frame indices (ED={selected_ed}, ES={selected_es}) "
                f"differ from trusted dataset Info.cfg expected values (ED={exp_ed}, ES={exp_es}). "
                f"Inference will proceed using your selected frames."
            )
            if user_confirmed:
                return (PhaseStatus.USER_CONFIRMED, warnings)
            else:
                raise ValidationError(
                    f"Selected frames (ED={selected_ed}, ES={selected_es}) differ from dataset Info.cfg (ED={exp_ed}, ES={exp_es}). "
                    f"Please confirm your override to proceed."
                )

    if user_confirmed:
        return (PhaseStatus.USER_CONFIRMED, warnings)

    # If arbitrary scan and not confirmed:
    raise ValidationError(
        "Phase Confirmation Required: For arbitrary uploaded scans without verified dataset metadata, "
        "explicit user confirmation of the ED and ES phase selections is required before running inference."
    )


# ==============================================================================
# 7. Comprehensive Master Validation Pipeline
# ==============================================================================

class MasterValidationResult:
    """Encapsulates sanitized, verified inputs ready for inference."""
    def __init__(
        self,
        ed_vol: np.ndarray,
        es_vol: np.ndarray,
        zooms: Tuple[float, float, float],
        ed_frame_1based: int,
        es_frame_1based: int,
        ed_frame_0based: int,
        es_frame_0based: int,
        patient_id: Optional[str],
        patient_id_verified: bool,
        verification_status: PhaseStatus,
        warnings: List[str],
        info_cfg: Optional[Dict[str, Any]]
    ):
        self.ed_vol = ed_vol
        self.es_vol = es_vol
        self.zooms = zooms
        self.ed_frame_1based = ed_frame_1based
        self.es_frame_1based = es_frame_1based
        self.ed_frame_0based = ed_frame_0based
        self.es_frame_0based = es_frame_0based
        self.patient_id = patient_id
        self.patient_id_verified = patient_id_verified
        self.verification_status = verification_status
        self.warnings = warnings
        self.info_cfg = info_cfg


def validate_pulse_inputs(
    mode: str,
    ed_nii: Optional[nib.Nifti1Image] = None,
    es_nii: Optional[nib.Nifti1Image] = None,
    cine_nii: Optional[nib.Nifti1Image] = None,
    ed_filename: str = "",
    es_filename: str = "",
    cine_filename: str = "",
    ed_frame_raw: Any = 1,
    es_frame_raw: Any = 14,
    user_confirmed: bool = True,
    trusted_info_cfg: Optional[Dict[str, Any]] = None,
) -> MasterValidationResult:
    """
    Central validation function executed BEFORE any model checkpoint loading or inference.
    """
    all_warnings: List[str] = []

    if mode == "paired":
        # 1. Require both volumes (no silent duplication)
        if ed_nii is None and es_nii is None:
            raise ValidationError("Paired mode requires both End-Diastole (ED) and End-Systole (ES) volumes. Neither was provided.")
        if ed_nii is None:
            raise ValidationError("Paired mode requires both ED and ES volumes. End-Diastole (ED) volume is missing.")
        if es_nii is None:
            raise ValidationError("Paired mode requires both ED and ES volumes. End-Systole (ES) volume is missing.")

        # Check identical file upload
        if ed_filename and es_filename and ed_filename == es_filename:
            raise ValidationError(
                f"Identical files provided for both ED and ES ('{ed_filename}'). "
                f"End-diastole and end-systole represent different cardiac phases and require distinct acquisitions."
            )

        # 2. Reject ground-truth masks
        for nii_obj, fname, role in [(ed_nii, ed_filename, "End-Diastole (ED)"), (es_nii, es_filename, "End-Systole (ES)")]:
            is_mask, is_susp, reason = inspect_is_segmentation_mask(nii_obj, fname)
            if is_mask:
                raise ValidationError(f"Rejected {role} volume: {reason}")
            if is_susp:
                all_warnings.append(f"Notice ({role}): {reason}")

        # 3. Patient ID mismatch detection
        pat_id, id_verified, id_notice = validate_patient_ids(ed_filename, es_filename)
        if id_notice:
            all_warnings.append(id_notice)

        # 4. Spatial compatibility
        zooms, spatial_warnings = validate_spatial_compatibility(ed_nii, es_nii)
        all_warnings.extend(spatial_warnings)

        # Extract volumes
        ed_vol = ed_nii.get_fdata().astype(np.float32)
        es_vol = es_nii.get_fdata().astype(np.float32)
        if ed_vol.ndim == 4:
            if ed_vol.shape[3] > 1:
                raise ValidationError(f"ED volume in paired mode is 4D (shape {ed_vol.shape}). Use 4D Cine mode for temporal series.")
            ed_vol = ed_vol[..., 0]
        if es_vol.ndim == 4:
            if es_vol.shape[3] > 1:
                raise ValidationError(f"ES volume in paired mode is 4D (shape {es_vol.shape}). Use 4D Cine mode for temporal series.")
            es_vol = es_vol[..., 0]

        # Check data arrays identical
        if np.array_equal(ed_vol, es_vol):
            raise ValidationError(
                "ED and ES voxel data arrays are identical. "
                "Paired cardiac functional analysis requires distinct systolic and diastolic volumes."
            )

        # 5. Evaluate phase confirmation status
        status, conf_warnings = evaluate_phase_verification(
            info_cfg=trusted_info_cfg,
            selected_ed=1,
            selected_es=2,
            user_confirmed=user_confirmed
        )
        all_warnings.extend(conf_warnings)

        return MasterValidationResult(
            ed_vol=ed_vol,
            es_vol=es_vol,
            zooms=zooms,
            ed_frame_1based=1,
            es_frame_1based=2,
            ed_frame_0based=0,
            es_frame_0based=1,
            patient_id=pat_id,
            patient_id_verified=id_verified,
            verification_status=status,
            warnings=all_warnings,
            info_cfg=trusted_info_cfg
        )

    elif mode == "cine4d":
        if cine_nii is None:
            raise ValidationError("4D Cine mode requires a 4D temporal cardiac MRI volume.")

        # Check ground truth mask
        is_mask, is_susp, reason = inspect_is_segmentation_mask(cine_nii, cine_filename)
        if is_mask:
            raise ValidationError(f"Rejected 4D Cine volume: {reason}")
        if is_susp:
            all_warnings.append(f"Notice (4D Cine): {reason}")

        # Validate Cine frame selections
        ed_1b, es_1b, ed_0b, es_0b = validate_cine_4d_frames(cine_nii, ed_frame_raw, es_frame_raw, cine_filename)

        data = cine_nii.get_fdata().astype(np.float32)
        ed_vol = data[..., ed_0b]
        es_vol = data[..., es_0b]
        zooms = tuple(round(float(z), 3) for z in cine_nii.header.get_zooms()[:3])

        pat_id = extract_patient_id(cine_filename)
        id_verified = pat_id is not None
        if not id_verified:
            all_warnings.append("Patient identity could not be established from 4D Cine filename.")

        # Check phase confirmation & Info.cfg
        status, conf_warnings = evaluate_phase_verification(
            info_cfg=trusted_info_cfg,
            selected_ed=ed_1b,
            selected_es=es_1b,
            user_confirmed=user_confirmed
        )
        all_warnings.extend(conf_warnings)

        return MasterValidationResult(
            ed_vol=ed_vol,
            es_vol=es_vol,
            zooms=zooms,
            ed_frame_1based=ed_1b,
            es_frame_1based=es_1b,
            ed_frame_0based=ed_0b,
            es_frame_0based=es_0b,
            patient_id=pat_id,
            patient_id_verified=id_verified,
            verification_status=status,
            warnings=all_warnings,
            info_cfg=trusted_info_cfg
        )

    else:
        raise ValidationError(f"Unknown analysis mode: '{mode}'. Must be 'paired' or 'cine4d'.")
