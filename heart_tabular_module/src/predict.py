"""
predict.py — Cascade inference for the heart disease tabular model.

Every patient passes through the two-stage cascade:

    Stage 1 (Anomaly Gate):   an Isolation Forest (1 % contamination, fitted on the
                              training set) flags implausible or extreme profiles.
                              Flagged patients are routed to manual clinical review.
    Stage 2 (Classification): survivors are scored by the calibrated Logistic Regression
                              model. The cost-optimal threshold from models/metadata.json
                              decides referral:
                                  Low Risk    < 0.2003
                                  Medium Risk   0.2003 – 0.50
                                  High Risk   >= 0.50
    Explanation:              the inputs that moved this patient's probability most
                              compared with a typical training patient.

Feature engineering and preprocessing happen inside the saved pipelines, so callers
supply only the 31 raw columns (see README.md or src/data.py::RAW_INPUT_COLUMNS).

Usage from Python:
    from src.predict import predict
    result = predict(patient_dict)
    result.status       # 'accepted' or 'review'
    result.label        # 'High Risk', 'Medium Risk', or 'Low Risk'
    result.probability  # float 0-1
    result.positive     # True if >= threshold
    result.message      # one-line summary

CLI (from heart_tabular_module/):
    python -m src.predict --input examples/patient.json
"""

from pathlib import Path

import pandas as pd

from common import Prediction
from common.tabular import TabularModel, run_cli
from . import data

_MODULE_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = _MODULE_ROOT / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "heart_disease_calibrated_model.joblib"
DEFAULT_ANOMALY_MODEL_PATH = MODEL_DIR / "heart_disease_anomaly_gate.joblib"
DEFAULT_METADATA_PATH = MODEL_DIR / "metadata.json"

REQUIRED_COLUMNS = data.RAW_INPUT_COLUMNS

MODEL = TabularModel(
    organ="heart", disease="heart disease", data_module=data,
    model_path=DEFAULT_MODEL_PATH, gate_path=DEFAULT_ANOMALY_MODEL_PATH, metadata_path=DEFAULT_METADATA_PATH,
    referral="refer for cardiology work-up (ECG, stress test)",
)


def predict(patient: dict, explain: bool = True) -> Prediction:
    """
    Run the cascade for one patient.

    Parameters
    ----------
    patient : dict
        A dict with the 31 raw input columns (NaN / None allowed for any field;
        the pipeline will KNN-impute numeric fields and mode-impute categoricals).
        See README.md for the complete feature schema.
    explain : bool
        If True (default), include which inputs moved the probability most.

    Returns
    -------
    Prediction
        .status       'accepted' | 'review'
        .label        'Low Risk' | 'Medium Risk' | 'High Risk' (None if review)
        .probability  float 0-1 (None if anomaly-gated)
        .positive     True if probability >= threshold (None if anomaly-gated)
        .message      one-line human-readable summary
        .explanation  dict with 'factors' list (empty if explain=False or review)
        .details      dict: disease, model, threshold, risk_bands, anomaly_flagged
    """
    return MODEL.predict(patient, explain=explain)


def predict_batch(patients: pd.DataFrame) -> pd.DataFrame:
    """
    Run the cascade for many patients.

    Parameters
    ----------
    patients : pd.DataFrame
        Each row is one patient with the 31 raw input columns.

    Returns
    -------
    pd.DataFrame
        Columns: status, label, probability, positive, message — one row per patient.
    """
    return MODEL.predict_batch(patients)


if __name__ == "__main__":
    run_cli(MODEL, "Run heart disease risk prediction (two-stage cascade: anomaly gate + calibrated LR).")
