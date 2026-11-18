"""Decoupled, fail-safe persistence service for PULSE computational runs.

Guarantees:
1. Failures in database writes never disrupt or fail clinical API responses.
2. Credentials, secrets, and raw PII are never logged.
3. Patient identifiers are partitioned by source_system to prevent cross-modal conflation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.db.models import AnalysisRun, MriAnalysis, Patient, RiskAssessment, SimulationRun
from backend.db.session import SessionLocal

logger = logging.getLogger("pulse.db.persistence")


def _get_or_create_patient(
    db: Session,
    source_system: str,
    patient_identifier: Optional[str],
    demographics: Optional[Dict[str, Any]] = None,
) -> Optional[UUID]:
    """Retrieves or registers a patient partitioned strictly by source_system."""
    if not patient_identifier or str(patient_identifier).strip() == "":
        return None

    ident_str = str(patient_identifier).strip()
    try:
        patient = (
            db.query(Patient)
            .filter(Patient.source_system == source_system, Patient.patient_identifier == ident_str)
            .first()
        )
        if patient:
            if demographics and not patient.demographics:
                patient.demographics = demographics
                db.flush()
            return patient.id

        new_patient = Patient(
            source_system=source_system,
            patient_identifier=ident_str,
            demographics=demographics or {},
        )
        db.add(new_patient)
        db.flush()
        return new_patient.id
    except SQLAlchemyError as exc:
        logger.warning("Patient record resolution deferred: %s", type(exc).__name__)
        return None


def persist_mri_analysis_run(
    result_dict: Dict[str, Any],
    mode: str,
    execution_time_ms: Optional[float] = None,
) -> Optional[UUID]:
    """Persists a successful volumetric MRI segmentation and diagnosis run."""
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        meta = result_dict.get("metadata", {})
        diagnosis = result_dict.get("diagnosis", {})
        biomarkers = result_dict.get("biomarkers", [])

        # Do not invent patient associations from MRI metadata or other untrusted identifiers.
        # Only associate if patient_id is explicitly verified by the validation pipeline.
        patient_id = None
        raw_id = meta.get("patient_id")
        if meta.get("patient_id_verified", False) and raw_id:
            source_system = "MRI_SAMPLE" if mode == "sample" else "MRI_ACQUISITION"
            patient_id = _get_or_create_patient(
                db,
                source_system=source_system,
                patient_identifier=str(raw_id),
                demographics={
                    "height_cm": meta.get("height_cm"),
                    "weight_kg": meta.get("weight_kg"),
                    "patient_bsa": meta.get("patient_bsa"),
                },
            )

        run = AnalysisRun(
            patient_id=patient_id,
            module_type="mri",
            status="SUCCESS",
            execution_time_ms=execution_time_ms,
            metadata_json={
                "mode": mode,
                "tta_enabled": meta.get("tta_enabled", False),
                "num_slices": meta.get("num_slices"),
                "dimensions": meta.get("dimensions"),
                "voxel_spacing": meta.get("voxel_spacing"),
            },
        )
        db.add(run)
        db.flush()

        # Confidence is on 0-100 scale from diagnosis output
        conf_val = diagnosis.get("confidence")
        if conf_val is not None:
            try:
                conf_val = float(conf_val)
            except (ValueError, TypeError):
                conf_val = None

        mri_entry = MriAnalysis(
            run_id=run.id,
            predicted_class=diagnosis.get("predicted_class", "UNKNOWN"),
            confidence=conf_val,
            class_probabilities=diagnosis.get("probabilities") or diagnosis.get("class_probabilities"),
            biomarkers=biomarkers,
            voxel_metadata={
                "num_slices": meta.get("num_slices"),
                "dimensions": meta.get("dimensions"),
                "voxel_spacing": meta.get("voxel_spacing"),
                "patient_bsa": meta.get("patient_bsa"),
                "verification_status": meta.get("verification_status"),
                "warnings": meta.get("warnings", []),
            },
        )
        db.add(mri_entry)
        db.commit()
        return run.id
    except Exception as exc:
        if db is not None:
            db.rollback()
        logger.warning("MRI analysis persistence skipped: %s", type(exc).__name__)
        return None
    finally:
        if db is not None:
            db.close()


def persist_tabular_risk_run(
    result_dict: Dict[str, Any],
    input_dict: Dict[str, Any],
    execution_time_ms: Optional[float] = None,
) -> Optional[UUID]:
    """Persists a successful CDC NHANES tabular cardiovascular risk prediction."""
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        # Tabular models are unlinked survey inputs unless explicit ID provided
        raw_id = input_dict.get("patient_id")
        patient_id = _get_or_create_patient(
            db,
            source_system="TABULAR_NHANES",
            patient_identifier=str(raw_id) if raw_id else None,
            demographics={
                "age": input_dict.get("age"),
                "gender": input_dict.get("gender"),
                "ethnicity": input_dict.get("ethnicity"),
                "bmi": input_dict.get("bmi"),
            },
        )

        run = AnalysisRun(
            patient_id=patient_id,
            module_type="tabular_risk",
            status="SUCCESS",
            execution_time_ms=execution_time_ms,
            metadata_json={
                "model": "CDC_NHANES_Calibrated_Classifier",
                "features_count": len(input_dict),
            },
        )
        db.add(run)
        db.flush()

        prob_val = float(result_dict.get("probability", 0.0))
        prob_val = max(0.0, min(1.0, prob_val))
        thresh_val = float(result_dict.get("threshold", 0.2003))
        thresh_val = max(0.0, min(1.0, thresh_val))

        assessment = RiskAssessment(
            run_id=run.id,
            risk_label=str(result_dict.get("label", "Unknown")),
            risk_probability=prob_val,
            threshold=thresh_val,
            positive=bool(result_dict.get("positive", False)),
            input_features=input_dict,
            contributing_factors=result_dict.get("factors", []),
        )
        db.add(assessment)
        db.commit()
        return run.id
    except Exception as exc:
        if db is not None:
            db.rollback()
        logger.warning("Tabular risk assessment persistence skipped: %s", type(exc).__name__)
        return None
    finally:
        if db is not None:
            db.close()


def persist_simulation_run(
    scenario_name: str,
    scenario_kind: str,
    preset_name: str,
    sim_params: Dict[str, Any],
    metrics: Dict[str, Any],
    deltas: Optional[List[Dict[str, Any]]] = None,
    subject_id: Optional[int] = None,
    session_id: Optional[str] = None,
    execution_time_ms: Optional[float] = None,
) -> Optional[UUID]:
    """Persists a successful CardioSim digital twin simulation run."""
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        # Link to MIMIC prototype cohort patient if subject_id is provided
        patient_id = None
        if subject_id:
            patient_id = _get_or_create_patient(
                db,
                source_system="MIMIC_PROTOTYPE",
                patient_identifier=str(subject_id),
            )

        run = AnalysisRun(
            patient_id=patient_id,
            module_type="cardio_twin",
            status="SUCCESS",
            execution_time_ms=execution_time_ms,
            metadata_json={
                "session_id": session_id,
                "engine": "CardioSim_ODE",
                "scenario_name": scenario_name,
                "preset_name": preset_name,
            },
        )
        db.add(run)
        db.flush()

        sim_entry = SimulationRun(
            run_id=run.id,
            session_id=session_id,
            scenario_name=scenario_name,
            scenario_kind=scenario_kind,
            preset_name=preset_name,
            parameters=sim_params,
            metrics=metrics,
            deltas=deltas,
        )
        db.add(sim_entry)
        db.commit()
        return run.id
    except Exception as exc:
        if db is not None:
            db.rollback()
        logger.warning("Simulation run persistence skipped: %s", type(exc).__name__)
        return None
    finally:
        if db is not None:
            db.close()

