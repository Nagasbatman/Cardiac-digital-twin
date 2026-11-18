"""Module III: Cardiovascular Digital Twin & CardioSim Simulation API routes.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

# Setup path for cardio_twin
BACKEND_DIR = Path(__file__).resolve().parent.parent
CARDIO_DIR = BACKEND_DIR / "cardio_twin"

import sys
if str(CARDIO_DIR) not in sys.path:
    sys.path.insert(0, str(CARDIO_DIR))

from cardiosim.client import (
    CardioSimClient,
    CardioSimConnectionError,
    CardioSimHTTPError,
    CardioSimResponseError,
    CardioSimTimeoutError,
)
from data.eligibility import build_hypothetical_preset_scenario
from data.loader import PrototypeDataLoader
from data.provenance import (
    PARAMETER_BOUNDS,
    PatientParameterResolver,
    ValidationError as ProvenanceValidationError,
    validate_simulation_duration,
)
from data.scenarios import (
    ScenarioConfiguration,
    ScenarioEngine,
    ScenarioKind,
    ScenarioRecord,
)
from services.presenter import (
    build_cardiovascular_analysis,
    build_clinical_trends,
    build_comparison_metrics,
    build_patient_summary,
    build_provenance_view,
    build_scenario_comparison_view,
    _format_display_name,
)
from services.session_store import global_scenario_store

LOG = logging.getLogger("cardio_twin_routes")
router = APIRouter(prefix="/api/cardio-twin", tags=["Module III: Cardiovascular Digital Twin"])

# Singleton loader for the 1,500 patient prototype
_loader = PrototypeDataLoader()


def _get_cardiosim_client() -> CardioSimClient:
    return CardioSimClient()


def _get_session_id(header_session_id: Optional[str] = None, param_session_id: Optional[str] = None) -> str:
    sid = header_session_id or param_session_id
    if not sid or sid.strip() == "":
        return "default-session"
    return sid.strip()


# Request Models
class SimulatePresetRequest(BaseModel):
    subject_id: int
    preset_name: str
    duration: float = Field(6.0, ge=2.0, le=20.0)
    compare_preset: Optional[str] = None
    session_id: Optional[str] = None


class RunWhatIfScenarioRequest(BaseModel):
    subject_id: Optional[int] = None
    scenario_name: str = "Custom What-If Scenario"
    preset_name: str = "Healthy Adult"
    hr: float = Field(..., ge=30.0, le=400.0)
    contract: float = Field(..., ge=10.0, le=160.0)
    resist: float = Field(..., ge=0.4, le=2.5)
    compl: float = Field(..., ge=0.6, le=2.2)
    duration: float = Field(6.0, ge=2.0, le=20.0)
    session_id: Optional[str] = None


# Endpoints

@router.get("/patients")
def list_patients(
    search: Optional[str] = Query(None, description="Search by subject_id prefix"),
    limit: int = Query(50, ge=1, le=1500),
    offset: int = Query(0, ge=0),
):
    """List available prototype patients and curated real cohort examples."""
    all_ids = _loader.list_subject_ids()
    total = len(all_ids)

    filtered = all_ids
    if search:
        s_clean = search.strip()
        filtered = [sid for sid in all_ids if s_clean in str(sid)]

    paginated = filtered[offset : offset + limit]

    # Curated real profiles from the prototype dataset
    curated_sample_ids = [10009482, 10010150, 10021818, 10024736, 10024982]
    sample_profiles = []
    for sid in curated_sample_ids:
        p = _loader.load_patient_record(sid)
        if p:
            sample_profiles.append({
                "subject_id": sid,
                "gender": p.demographics.gender,
                "anchor_age": p.demographics.anchor_age,
                "anchor_year_group": p.demographics.anchor_year_group,
                "observation_count": len(p.observations),
                "distinct_dates": len({o.event_date for o in p.observations if o.event_date}),
            })

    return {
        "total_patients": total,
        "filtered_count": len(filtered),
        "limit": limit,
        "offset": offset,
        "patient_ids": paginated,
        "sample_profiles": sample_profiles,
    }


@router.get("/patients/{subject_id}")
def get_patient_profile(subject_id: int):
    """Retrieve full demographic summary and eligibility status for a patient."""
    patient = _loader.load_patient_record(subject_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {subject_id} not found in prototype dataset.")

    summary = build_patient_summary(patient)
    return {
        "success": True,
        "summary": summary,
        "subject_id": subject_id,
    }


@router.get("/patients/{subject_id}/observations")
def get_patient_observations(
    subject_id: int,
    category: Optional[str] = Query(None, description="Filter by clinical category"),
    measurement_name: Optional[str] = Query(None, description="Filter by measurement name"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve longitudinal clinical observations with filters and pagination."""
    patient = _loader.load_patient_record(subject_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {subject_id} not found in prototype dataset.")

    obs = patient.observations
    if measurement_name:
        obs = [o for o in obs if o.measurement_name == measurement_name]

    total_filtered = len(obs)
    paginated = obs[offset : offset + limit]

    obs_dicts = [
        {
            "measurement_name": o.measurement_name,
            "display_name": _format_display_name(o.measurement_name),
            "value_numeric": o.value_numeric,
            "measurement_unit": o.measurement_unit,
            "event_date": o.event_date,
            "event_time": o.event_time,
            "source": o.source,
            "source_label": o.source_label,
            "hadm_id": o.hadm_id,
            "value_review_status": o.value_review_status,
            "usable_for_patient_analysis": o.usable_for_patient_analysis,
        }
        for o in paginated
    ]

    return {
        "total": total_filtered,
        "limit": limit,
        "offset": offset,
        "observations": obs_dicts,
    }


@router.get("/patients/{subject_id}/trends")
def get_patient_trends(subject_id: int):
    """Retrieve longitudinal trends grouped by category for charting."""
    patient = _loader.load_patient_record(subject_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {subject_id} not found in prototype dataset.")

    trends = build_clinical_trends(patient)
    # Strip non-serializable objects and return clean structured data
    clean_trends = []
    for t in trends:
        clean_trends.append({
            "category": t.get("category"),
            "unit": t.get("unit"),
            "data_table": t.get("data_table", []),
            "svg_chart": str(t.get("svg_chart", "")),
        })

    return {
        "subject_id": subject_id,
        "trends": clean_trends,
    }


@router.get("/patients/{subject_id}/analysis")
def get_patient_analysis(subject_id: int):
    """Retrieve categorized domain summaries and data quality review flags."""
    patient = _loader.load_patient_record(subject_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {subject_id} not found in prototype dataset.")

    analysis = build_cardiovascular_analysis(patient)
    return {
        "subject_id": subject_id,
        "analysis": analysis,
    }


@router.get("/patients/{subject_id}/provenance")
def get_patient_provenance(subject_id: int):
    """Evaluate simulation parameter provenance (MEASURED, ESTIMATED, ASSUMED, UNAVAILABLE)."""
    patient = _loader.load_patient_record(subject_id)
    provenance = build_provenance_view(patient)
    return {
        "subject_id": subject_id,
        "provenance": provenance,
        "parameter_bounds": PARAMETER_BOUNDS,
    }


@router.get("/presets")
def get_presets():
    """Retrieve available presets from CardioSim, falling back to built-in defaults if offline."""
    client = _get_cardiosim_client()
    try:
        presets = client.get_presets()
        serializable_presets = {}
        for name, info in presets.items():
            serializable_presets[name] = {
                "name": info.name,
                "hr": info.hr,
                "contract": info.contract,
                "resist": info.resist,
                "compl": info.compl,
                "desc": info.desc,
                "category": info.category,
            }
        return {
            "success": True,
            "cardiosim_live": True,
            "presets": serializable_presets,
            "parameter_bounds": PARAMETER_BOUNDS,
        }
    except (CardioSimConnectionError, CardioSimTimeoutError):
        # CardioSim is offline — return the built-in preset definitions so the
        # UI can still render preset names and parameters. Simulations will fail
        # separately when the user actually tries to run one.
        LOG.warning("CardioSim offline — serving built-in preset fallback for /presets")
        return {
            "success": True,
            "cardiosim_live": False,
            "cardiosim_offline_notice": (
                "CardioSim engine is currently offline (port 8000). "
                "Preset parameters shown are built-in defaults. "
                "Simulations will be unavailable until CardioSim is started."
            ),
            "presets": _builtin_presets_fallback(),
            "parameter_bounds": PARAMETER_BOUNDS,
        }
    except CardioSimHTTPError as exc:
        # Treat an upstream 5xx (including CardioSim's own 503 maintenance
        # response) as unavailable for preset discovery. The UI can still
        # render with built-in presets; simulation calls report their own error.
        if exc.status_code < 500:
            raise HTTPException(
                status_code=502,
                detail=f"CardioSim rejected the preset request: {exc.detail}",
            ) from exc
        LOG.warning(
            "CardioSim preset endpoint returned HTTP %s; serving built-in fallback",
            exc.status_code,
        )
        return {
            "success": True,
            "cardiosim_live": False,
            "cardiosim_offline_notice": (
                f"CardioSim preset service returned HTTP {exc.status_code}. "
                "Built-in presets are shown; simulations may be unavailable."
            ),
            "presets": _builtin_presets_fallback(),
            "parameter_bounds": PARAMETER_BOUNDS,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error querying CardioSim presets: {exc}")


def _builtin_presets_fallback() -> dict:
    """Return the CardioSim built-in preset definitions without needing a live connection."""
    return {
        "Healthy Adult":            {"name": "Healthy Adult",            "hr": 75,  "contract": 100, "resist": 1.0, "compl": 1.46, "desc": "Resting baseline: heart rate 75 bpm, contractility 100%. Cardiac output 4.64 L/min, blood pressure 113/68 mmHg.", "category": "normal"},
        "Hypertension":             {"name": "Hypertension",             "hr": 80,  "contract": 110, "resist": 1.5, "compl": 1.1,  "desc": "Peripheral resistance 1.5 mmHg·s/mL, arterial compliance 1.10 mL/mmHg, contractility 110%, heart rate 80 bpm. Blood pressure 140/95 mmHg.", "category": "structural"},
        "Heart Failure (Systolic)": {"name": "Heart Failure (Systolic)", "hr": 90,  "contract": 55,  "resist": 1.2, "compl": 1.46, "desc": "Contractility reduced to 55%, heart rate 90 bpm, peripheral resistance 1.2 mmHg·s/mL. Ejection fraction 29%; cardiac output 2.97 L/min.", "category": "structural"},
        "Sinus Tachycardia":        {"name": "Sinus Tachycardia",        "hr": 120, "contract": 100, "resist": 1.0, "compl": 1.46, "desc": "Regular rhythm at 120 bpm, contractility 100%. Stroke volume falls to 46 mL; cardiac output 5.55 L/min.", "category": "arrhythmia"},
        "Sinus Bradycardia":        {"name": "Sinus Bradycardia",        "hr": 50,  "contract": 100, "resist": 1.0, "compl": 1.46, "desc": "Regular rhythm at 50 bpm, contractility 100%. Longer filling raises stroke volume to 76 mL, cardiac output 3.81 L/min.", "category": "arrhythmia"},
        "Atrial Fibrillation":      {"name": "Atrial Fibrillation",      "hr": 130, "contract": 85,  "resist": 1.0, "compl": 1.46, "desc": "Irregular R-R intervals, contractility 85%.", "category": "arrhythmia"},
        "Ventricular Tachycardia":  {"name": "Ventricular Tachycardia",  "hr": 180, "contract": 60,  "resist": 1.0, "compl": 1.46, "desc": "Regular rhythm at 180 bpm with contractility reduced to 60%. Stroke volume 23 mL; cardiac output 4.18 L/min.", "category": "arrhythmia"},
        "Ventricular Fibrillation": {"name": "Ventricular Fibrillation", "hr": 350, "contract": 25,  "resist": 1.0, "compl": 1.46, "desc": "Irregular VF-like rhythm, contractility 25%. Cardiac output falls 57% from Healthy Adult.", "category": "critical"},
        "Aortic Stenosis":          {"name": "Aortic Stenosis",          "hr": 80,  "contract": 120, "resist": 1.0, "compl": 1.46, "desc": "Aortic valve resistance raised, contractility 120%, heart rate 80 bpm.", "category": "structural"},
        "Diabetes (T2D Metabolic)": {"name": "Diabetes (T2D Metabolic)", "hr": 82,  "contract": 95,  "resist": 1.3, "compl": 1.2,  "desc": "Type 2 diabetes metabolic cardiovascular profile: mild peripheral resistance elevation, reduced arterial compliance.", "category": "metabolic"},
    }


@router.post("/simulate")
def run_simulation(req: SimulatePresetRequest, x_session_id: Optional[str] = Header(None)):
    """Run an explicitly chosen generic preset simulation via CardioSim."""
    session_id = _get_session_id(x_session_id, req.session_id)
    client = _get_cardiosim_client()

    patient = _loader.load_patient_record(req.subject_id)
    try:
        presets = client.get_presets()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot connect to CardioSim backend: {exc}")

    if req.preset_name not in presets:
        raise HTTPException(status_code=400, detail=f"Unknown preset '{req.preset_name}'.")

    if req.compare_preset and req.compare_preset not in presets:
        raise HTTPException(status_code=400, detail=f"Unknown comparison preset '{req.compare_preset}'.")

    pinfo = presets[req.preset_name]
    preset_settings = {
        "hr": pinfo.hr,
        "contract": pinfo.contract,
        "resist": pinfo.resist,
        "compl": pinfo.compl,
    }

    try:
        scenario = build_hypothetical_preset_scenario(
            preset_name=req.preset_name,
            preset_settings=preset_settings,
            duration=req.duration,
            patient=patient,
            compare_preset=req.compare_preset,
        )

        sim_response = client.simulate(**scenario.to_client_payload())

        # Save baseline to session store
        engine = ScenarioEngine(client)
        baseline_config = engine.build_generic_baseline(
            preset_name=req.preset_name,
            presets_dict=presets,
            duration=req.duration,
            patient=patient,
        )
        baseline_record = ScenarioRecord(
            configuration=baseline_config,
            sim_result=sim_response.primary,
            deltas_from_baseline=[],
            metric_comparisons=[],
        )
        global_scenario_store.add_scenario(session_id, baseline_record)

        # Build side-by-side comparison if compare_preset provided
        comparison = build_comparison_metrics(sim_response, req.preset_name, req.compare_preset, presets)

        return {
            "success": True,
            "scenario_label": scenario.label,
            "scenario_disclaimer": scenario.disclaimer,
            "sim_params": preset_settings,
            "duration": req.duration,
            "metrics": {
                "co": sim_response.primary.metrics.co,
                "sv": sim_response.primary.metrics.sv,
                "sys": sim_response.primary.metrics.sys,
                "dia": sim_response.primary.metrics.dia,
                "map_val": sim_response.primary.metrics.map_val,
                "pp": sim_response.primary.metrics.pp,
                "ef": sim_response.primary.metrics.ef,
                "hr": sim_response.primary.metrics.hr,
            },
            "comparison": comparison,
        }
    except CardioSimConnectionError as exc:
        raise HTTPException(status_code=503, detail=f"Cannot reach CardioSim backend: {exc}")
    except CardioSimHTTPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=f"CardioSim simulation rejected: {exc.detail}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")


@router.post("/scenarios/run")
def run_custom_scenario(req: RunWhatIfScenarioRequest, x_session_id: Optional[str] = Header(None)):
    """Run an independent what-if scenario with authoritative parameter validation."""
    session_id = _get_session_id(x_session_id, req.session_id)
    client = _get_cardiosim_client()

    patient = _loader.load_patient_record(req.subject_id) if req.subject_id else None

    try:
        presets = client.get_presets()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Cannot connect to CardioSim backend: {exc}")

    if req.preset_name not in presets:
        raise HTTPException(status_code=400, detail=f"Unknown preset '{req.preset_name}'.")

    engine = ScenarioEngine(client)
    session_scenarios = global_scenario_store.get_scenarios(session_id)

    # Find or execute matching baseline
    ref_cfg = engine.build_generic_baseline(req.preset_name, presets, req.duration, patient)
    baseline_record = next(
        (
            record
            for record in session_scenarios
            if record.configuration.kind == ScenarioKind.GENERIC_BASELINE
            and record.configuration.preset == ref_cfg.preset
            and record.configuration.duration == ref_cfg.duration
            and record.configuration.hr == ref_cfg.hr
            and record.configuration.contract == ref_cfg.contract
            and record.configuration.resist == ref_cfg.resist
            and record.configuration.compl == ref_cfg.compl
            and record.sim_result is not None
        ),
        None,
    )
    if baseline_record is None:
        baseline_record = engine.run_scenario(ref_cfg)
        if baseline_record.execution_error or baseline_record.sim_result is None:
            raise HTTPException(
                status_code=502,
                detail=f"Could not initialize reference baseline: {baseline_record.execution_error or 'No result'}"
            )
        global_scenario_store.add_scenario(session_id, baseline_record)

    try:
        custom_cfg, deltas = engine.create_custom_scenario(
            name=req.scenario_name,
            baseline_config=baseline_record.configuration,
            hr=req.hr,
            contract=req.contract,
            resist=req.resist,
            compl=req.compl,
            duration=req.duration,
            patient=patient,
        )

        new_record = engine.run_scenario(custom_cfg, baseline_record)
        if new_record.execution_error:
            raise HTTPException(status_code=422, detail=f"CardioSim simulation failed: {new_record.execution_error}")

        global_scenario_store.add_scenario(session_id, new_record)
        all_scenarios = global_scenario_store.get_scenarios(session_id)

        comparison_view = build_scenario_comparison_view(baseline_record, new_record, all_scenarios)
        return {
            "success": True,
            "scenario": new_record.to_summary_dict(),
            "comparison": comparison_view,
        }
    except ProvenanceValidationError as val_err:
        raise HTTPException(status_code=400, detail=f"Validation Error: {val_err}")
    except (CardioSimConnectionError, CardioSimTimeoutError) as exc:
        raise HTTPException(status_code=503, detail=f"CardioSim backend connection error: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scenario execution failed: {exc}")


@router.get("/scenarios")
def get_scenarios(x_session_id: Optional[str] = Header(None), session_id: Optional[str] = Query(None)):
    """Retrieve session what-if scenario history and active comparison."""
    sid = _get_session_id(x_session_id, session_id)
    scenarios = global_scenario_store.get_scenarios(sid)
    baseline_record = scenarios[0] if scenarios else None
    current_scenario = scenarios[-1] if len(scenarios) > 1 else None

    comparison_view = build_scenario_comparison_view(baseline_record, current_scenario, scenarios)
    return {
        "session_id": sid,
        "scenarios": [s.to_summary_dict() for s in scenarios],
        "comparison": comparison_view,
    }


@router.delete("/scenarios")
def clear_scenarios(x_session_id: Optional[str] = Header(None), session_id: Optional[str] = Query(None)):
    """Clear temporary in-memory scenario history for current session."""
    sid = _get_session_id(x_session_id, session_id)
    global_scenario_store.clear_session(sid)
    return {"success": True, "message": f"Scenario history cleared for session {sid}."}

