# Heart Disease Tabular Risk Module

A fully independent, portable Python module that predicts heart disease risk from
31 clinical/patient tabular features using a pretrained two-stage cascade.

**No training occurs here.** This module uses the exact pretrained model artifacts
from the original `Disease-Prediction-System` repository.

---

## What This Module Does

Predicts the presence of **heart disease** (coronary heart disease, angina, heart
attack, or congestive heart failure) from demographic, vital-sign, laboratory,
lifestyle, and chest-pain data.

Dataset: **CDC NHANES 2007–March 2020** — 24,454 examined adults aged 40+,
31 features, 12.5 % heart disease prevalence.

---

## Trained Model

| Property | Value |
|---|---|
| **Model** | Calibrated Logistic Regression (isotonic calibration) |
| **Selection** | One-standard-error rule on 5-fold CV PR-AUC among 17 candidates |
| **Decision threshold** | 0.2003 (cost-optimal: 5× penalty for missed cases) |
| **Test ROC-AUC** | 0.880 (95 % CI: 0.866–0.893) |
| **Test PR-AUC** | 0.555 (95 % CI: 0.515–0.597) |
| **Recall at threshold** | 0.731 (95 % CI: 0.696–0.767) |
| **Precision at threshold** | 0.416 (95 % CI: 0.386–0.446) |
| **Training rows** | 19,563 |
| **Test rows** | 4,891 |

---

## Two-Stage Cascade

1. **Stage 1 — Anomaly Gate** (`heart_disease_anomaly_gate.joblib`):
   An Isolation Forest (200 estimators, 1 % contamination) trained on the
   training set's numeric features. Profiles that fall in the anomaly region
   are withheld from Stage 2 and flagged for manual clinical review.

2. **Stage 2 — Classification** (`heart_disease_calibrated_model.joblib`):
   The calibrated Logistic Regression pipeline. The preprocessing pipeline
   (feature engineering → RobustScaler + KNNImputer → OneHotEncoder) lives
   *inside* the saved joblib, so callers supply only the 31 raw input columns.

---

## Input Features (31 Raw Columns)

The model expects the following columns in this exact order
(missing values are allowed — the pipeline imputes them):

| # | Column | Type | Values / Range |
|---|--------|------|----------------|
| 1 | `age` | numerical | years, 18–100 |
| 2 | `gender` | categorical | "Female", "Male" |
| 3 | `ethnicity` | categorical | "Mexican American", "Non-Hispanic Black", "Non-Hispanic White", "Non-Hispanic Asian", "Other Hispanic", "Other/Multi-Racial" |
| 4 | `education_level` | numerical (ordinal) | 1=< 9th grade, 2=9–11th, 3=HS/GED, 4=Some college, 5=College grad |
| 5 | `poverty_income_ratio` | numerical | 0.0–5.0 (5 = 5× or more) |
| 6 | `bmi` | numerical | kg/m², 10–80 |
| 7 | `waist_cm` | numerical | cm, 40–200 |
| 8 | `height_cm` | numerical | cm, 120–220 |
| 9 | `systolic_bp` | numerical | mm Hg, 50–300 |
| 10 | `diastolic_bp` | numerical | mm Hg, 20–200 |
| 11 | `resting_heart_rate` | numerical | bpm, 30–200 |
| 12 | `total_cholesterol` | numerical | mg/dL, 50–500 |
| 13 | `hdl_cholesterol` | numerical | mg/dL, 10–150 |
| 14 | `hba1c` | numerical | %, 3.0–18.0 |
| 15 | `serum_creatinine` | numerical | mg/dL, 0.2–15.0 |
| 16 | `uric_acid` | numerical | mg/dL, 1.0–15.0 |
| 17 | `albumin_creatinine_ratio` | numerical | mg/g, 0–5000 |
| 18 | `white_blood_cells` | numerical | 10³/µL, 1–50 |
| 19 | `hemoglobin` | numerical | g/dL, 5–20 |
| 20 | `rdw` | numerical | %, 10–30 |
| 21 | `smoking_status` | categorical | "Never", "Former", "Current" |
| 22 | `physically_active` | categorical | "Yes", "No" |
| 23 | `hypertension_history` | categorical | "Yes", "No" |
| 24 | `high_cholesterol_history` | categorical | "Yes", "No" |
| 25 | `diabetes_status` | categorical | "Yes", "No" |
| 26 | `stroke_history` | categorical | "Yes", "No" |
| 27 | `family_history_chd` | categorical | "Yes", "No" |
| 28 | `general_health` | numerical (ordinal) | 1=Excellent, 2=Very good, 3=Good, 4=Fair, 5=Poor |
| 29 | `chest_pain_type` | categorical | "No pain", "Non-exertional", "Exertional", "Typical angina" |
| 30 | `severe_chest_pain` | categorical | "Yes", "No" |
| 31 | `sob_on_exertion` | categorical | "Yes", "No" |

> **Missing values:** Any field may be None / NaN. The pipeline KNN-imputes
> numerical fields and mode-imputes categorical fields. Very sparse inputs
> (< 5 known fields) may produce unreliable estimates.

---

## Engineered Features (computed internally by the pipeline)

These 7 features are computed automatically inside the saved pipeline.
You do **not** need to compute them yourself:

| Feature | Formula |
|---------|---------|
| `pulse_pressure` | systolic_bp − diastolic_bp |
| `non_hdl_cholesterol` | total_cholesterol − hdl_cholesterol |
| `tc_hdl_ratio` | total_cholesterol / max(hdl_cholesterol, 10) |
| `waist_to_height_ratio` | waist_cm / height_cm |
| `egfr` | Race-free CKD-EPI 2021 creatinine eGFR (mL/min/1.73 m²) |
| `log_acr` | log₁₀(albumin_creatinine_ratio, floor 0.1) |
| `risk_factor_count` | Count of {hypertension, high cholesterol, diabetes, current smoking} |

---

## Output Classes / Risk Categories

| Status | Label | Condition |
|--------|-------|-----------|
| `accepted` | `Low Risk` | P(disease) < 0.2003 |
| `accepted` | `Medium Risk` | 0.2003 ≤ P(disease) < 0.50 |
| `accepted` | `High Risk` | P(disease) ≥ 0.50 |
| `review` | None | Anomaly gate flagged the profile |

---

## Folder Structure

```
heart_tabular_module/
├── app.py                              # Streamlit UI entry point
├── requirements.txt                    # Pinned dependencies
├── README.md                           # This file
├── models/
│   ├── heart_disease_calibrated_model.joblib  # Stage 2: calibrated LR
│   ├── heart_disease_anomaly_gate.joblib      # Stage 1: Isolation Forest
│   ├── metadata.json                          # threshold, features, metrics
│   └── reference_profile.json                # typical training patient
├── examples/
│   └── patient.json                    # High-risk example input
├── src/
│   ├── __init__.py                     # adds module root to sys.path
│   ├── data.py                         # feature schema + add_custom_features
│   └── predict.py                      # predict() / predict_batch() API
└── common/
    ├── __init__.py
    ├── prediction.py                   # Prediction dataclass
    ├── tabular.py                      # TabularModel cascade class
    └── utils/
        ├── __init__.py
        └── artifacts.py               # joblib pipeline loader
```

---

## Installation

```bash
# 1. Navigate to this folder
cd heart_tabular_module

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Important:** `scikit-learn==1.8.0` and `imbalanced-learn==0.14.1` are pinned
> because joblib pickles embed the exact scikit-learn class structure. Mismatched
> versions will cause `AttributeError` or `ImportError` on load.

---

## Launching the UI

```bash
# From heart_tabular_module/
streamlit run app.py
```

Opens at http://localhost:8501 by default.

---

## Using the Python API

```python
import sys
sys.path.insert(0, "/path/to/heart_tabular_module")   # or copy the folder into your project

from src.predict import predict, predict_batch
import pandas as pd

# ── Single patient ────────────────────────────────────────────────────────
result = predict({
    "age": 67, "gender": "Male", "ethnicity": "Non-Hispanic White", "education_level": 2,
    "poverty_income_ratio": 1.3, "bmi": 31.5, "waist_cm": 112, "height_cm": 175,
    "systolic_bp": 158, "diastolic_bp": 84, "resting_heart_rate": 82,
    "total_cholesterol": 240, "hdl_cholesterol": 34, "hba1c": 7.9, "serum_creatinine": 1.4,
    "uric_acid": 7.6, "albumin_creatinine_ratio": 85, "white_blood_cells": 8.9,
    "hemoglobin": 13.4, "rdw": 14.8, "smoking_status": "Current", "physically_active": "No",
    "hypertension_history": "Yes", "high_cholesterol_history": "Yes", "diabetes_status": "Yes",
    "stroke_history": "No", "family_history_chd": "Yes", "general_health": 4,
    "chest_pain_type": "Exertional", "severe_chest_pain": "Yes", "sob_on_exertion": "Yes",
})

result.status      # 'accepted'
result.label       # 'High Risk'
result.probability # ~0.924
result.positive    # True
result.message     # 'High Risk (92%): refer for cardiology work-up (ECG, stress test)'
result.explanation["factors"][:2]
# [{'feature': 'chest_pain_type', 'value': 'Exertional', 'typical': 'No pain', 'effect': 0.256},
#  {'feature': 'severe_chest_pain', 'value': 'Yes', 'typical': 'No', 'effect': 0.180}]

# ── With missing values ────────────────────────────────────────────────────
result_sparse = predict({
    "age": 67, "gender": "Male", "systolic_bp": 158, "diastolic_bp": 84,
    "chest_pain_type": "Exertional", "severe_chest_pain": "Yes",
    # all other 25 fields left as None → will be imputed
})

# ── Batch prediction ──────────────────────────────────────────────────────
df = pd.read_json("examples/patient.json")  # or any DataFrame with the 31 columns
batch_results = predict_batch(df)
# Returns DataFrame: status, label, probability, positive, message

# ── CLI ───────────────────────────────────────────────────────────────────
# python -m src.predict --input examples/patient.json
```

---

## CLI Test

```bash
# From heart_tabular_module/
python -m src.predict --input examples/patient.json
```

Expected output (approximately):
```json
{
  "organ": "heart",
  "modality": "tabular",
  "status": "accepted",
  "label": "High Risk",
  "probability": 0.924,
  "positive": true,
  "message": "High Risk (92%): refer for cardiology work-up (ECG, stress test)",
  ...
}
```

---

## Known Limitations

- **Calibration:** The model uses isotonic calibration trained on the same NHANES cohort.
  Probabilities may not generalise perfectly to other populations.
- **Self-reported diagnosis:** The `heart_disease` target in NHANES is self-reported.
  Undiagnosed cases are labelled as negative.
- **Cross-sectional data:** NHANES is not longitudinal; it cannot capture incident events.
- **Statin/antihypertensive effect:** Diagnosed patients often have treated
  cholesterol/BP, so the model may see lower values in disease cases.
- **Anomaly gate:** 1 % contamination means ~1 % of healthy profiles may be flagged.
  The gate is conservative by design.
- **Not a medical device:** For research and educational use only.

---

## Confirming No Training Occurred

- No model was trained, retrained, or fine-tuned.
- No checkpoint or model weights were modified.
- No new model was generated.
- The `models/*.joblib` files are verbatim copies from the original repository's
  `models/heart/tabuler/models/` directory.
- `src/data.py` is an exact copy of the original `src/data.py` — including the
  `add_custom_features` function that the saved pipelines reference by name.
