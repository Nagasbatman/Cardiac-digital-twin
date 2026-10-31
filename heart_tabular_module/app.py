"""
app.py — Standalone Streamlit UI for the Heart Disease Tabular Risk Module.

This is a focused, independent extraction of the heart questionnaire from the
original frontend/app/stremlit_app.py. It uses ONLY the heart tabular model
and does NOT require the kidney, lung, image, or triage modules.

Run from heart_tabular_module/:
    streamlit run app.py
"""

import json
import sys
from pathlib import Path

# Ensure the module root is on sys.path so `from src import ...` works
_MODULE_ROOT = Path(__file__).resolve().parent
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

import streamlit as st
import pandas as pd

from src.predict import predict, MODEL, REQUIRED_COLUMNS

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Heart Disease Risk Predictor",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Feature Schema ───────────────────────────────────────────────────────────
# Exact values the model was trained on (from reference_profile.json + metadata.json)
GENDER_OPTIONS     = ["Female", "Male"]
ETHNICITY_OPTIONS  = ["Mexican American", "Non-Hispanic Black", "Non-Hispanic White",
                      "Non-Hispanic Asian", "Other Hispanic", "Other/Multi-Racial"]
SMOKING_OPTIONS    = ["Never", "Former", "Current"]
YESNO_OPTIONS      = ["No", "Yes"]
CHEST_PAIN_OPTIONS = ["No pain", "Non-exertional", "Exertional", "Typical angina"]
HEALTH_OPTIONS     = {1: "Excellent", 2: "Very good", 3: "Good", 4: "Fair", 5: "Poor"}
EDU_OPTIONS        = {1: "< 9th grade", 2: "9th–11th grade", 3: "High school / GED",
                      4: "Some college", 5: "College graduate"}

EXAMPLE_PATIENT = {
    "age": 67, "gender": "Male", "ethnicity": "Non-Hispanic White", "education_level": 2,
    "poverty_income_ratio": 1.3, "bmi": 31.5, "waist_cm": 112.0, "height_cm": 175.0,
    "systolic_bp": 158, "diastolic_bp": 84, "resting_heart_rate": 82,
    "total_cholesterol": 240, "hdl_cholesterol": 34, "hba1c": 7.9, "serum_creatinine": 1.4,
    "uric_acid": 7.6, "albumin_creatinine_ratio": 85.0, "white_blood_cells": 8.9,
    "hemoglobin": 13.4, "rdw": 14.8, "smoking_status": "Current", "physically_active": "No",
    "hypertension_history": "Yes", "high_cholesterol_history": "Yes", "diabetes_status": "Yes",
    "stroke_history": "No", "family_history_chd": "Yes", "general_health": 4,
    "chest_pain_type": "Exertional", "severe_chest_pain": "Yes", "sob_on_exertion": "Yes",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def selectbox_or_none(label, options, default=None, key=None):
    """Selectbox where the user can leave the value unknown (None)."""
    idx = None
    if default is not None and default in options:
        idx = options.index(default)
    return st.selectbox(label, options, index=idx, placeholder="unknown (will be imputed)", key=key)


def number_or_none(label, min_val, max_val, step, default=None, format_str=None, key=None):
    kwargs = dict(min_value=min_val, max_value=max_val, step=step,
                  placeholder="unknown (will be imputed)", value=default, key=key)
    if format_str:
        kwargs["format"] = format_str
    return st.number_input(label, **kwargs)


def load_example():
    st.session_state["example_loaded"] = True


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🫀 Heart Disease Risk")
    st.markdown(
        "**CDC NHANES tabular model** — 24,454 adults 40+, 12.5 % prevalence.\n\n"
        "Two-stage cascade:\n"
        "1. **Anomaly Gate** (Isolation Forest) — filters implausible profiles\n"
        "2. **Calibrated Logistic Regression** — P(heart disease)\n\n"
        f"Decision threshold: **0.2003** (5× cost for missed cases)"
    )
    st.divider()
    st.button("📋 Load example patient", on_click=load_example, use_container_width=True)
    with st.expander("ℹ️ Disclaimer"):
        st.caption(
            "Research model trained on public CDC NHANES data. Not a medical device. "
            "If you have cardiac symptoms, consult a physician immediately."
        )

# ─── Main Form ───────────────────────────────────────────────────────────────
ex = EXAMPLE_PATIENT if st.session_state.get("example_loaded") else {}

st.title("Heart Disease Risk Questionnaire")
st.caption("Answer as many fields as you know. Unknown values are imputed by the model (KNN for numbers, "
           "most-frequent-answer for categories). The model requires at least some inputs to be reliable.")

with st.form("heart_form"):

    # ── About You ────────────────────────────────────────────────────────────
    st.subheader("👤 About You")
    c1, c2, c3 = st.columns(3)
    with c1:
        age = st.number_input("Age (years)", min_value=18, max_value=100, step=1,
                              value=ex.get("age"), placeholder="required", key="age")
    with c2:
        gender = selectbox_or_none("Sex", GENDER_OPTIONS, ex.get("gender"), key="gender")
    with c3:
        ethnicity = selectbox_or_none("Ethnicity", ETHNICITY_OPTIONS, ex.get("ethnicity"), key="ethnicity")

    c4, c5 = st.columns(2)
    with c4:
        education_level = st.selectbox(
            "Education", list(EDU_OPTIONS.keys()),
            index=list(EDU_OPTIONS.keys()).index(ex.get("education_level")) if ex.get("education_level") in EDU_OPTIONS else None,
            format_func=lambda v: EDU_OPTIONS[v], placeholder="unknown", key="education_level",
        )
    with c5:
        poverty_income_ratio = number_or_none("Family income ÷ poverty line (0–5)",
                                              0.0, 5.0, 0.1, ex.get("poverty_income_ratio"), "%.1f", "pir")

    # ── Measurements ─────────────────────────────────────────────────────────
    st.subheader("📏 Measurements")
    c1, c2, c3 = st.columns(3)
    with c1:
        height_cm = number_or_none("Height (cm)", 120.0, 220.0, 0.5, ex.get("height_cm"), "%.1f", "height")
        bmi       = number_or_none("BMI (kg/m²)", 10.0, 80.0, 0.1, ex.get("bmi"), "%.1f", "bmi")
        waist_cm  = number_or_none("Waist (cm)", 40.0, 200.0, 0.5, ex.get("waist_cm"), "%.1f", "waist")
    with c2:
        systolic_bp        = number_or_none("Systolic BP (mm Hg)", 50, 300, 1, ex.get("systolic_bp"), key="sbp")
        diastolic_bp       = number_or_none("Diastolic BP (mm Hg)", 20, 200, 1, ex.get("diastolic_bp"), key="dbp")
        resting_heart_rate = number_or_none("Resting heart rate (bpm)", 30, 200, 1, ex.get("resting_heart_rate"), key="rhr")

    # ── Lab Results ──────────────────────────────────────────────────────────
    st.subheader("🧪 Lab Results")
    c1, c2, c3 = st.columns(3)
    with c1:
        total_cholesterol        = number_or_none("Total cholesterol (mg/dL)", 50, 500, 1, ex.get("total_cholesterol"), key="tc")
        hdl_cholesterol          = number_or_none("HDL cholesterol (mg/dL)", 10, 150, 1, ex.get("hdl_cholesterol"), key="hdl")
        hba1c                    = number_or_none("HbA1c (%)", 3.0, 18.0, 0.1, ex.get("hba1c"), "%.1f", "hba1c")
    with c2:
        serum_creatinine         = number_or_none("Serum creatinine (mg/dL)", 0.2, 15.0, 0.1, ex.get("serum_creatinine"), "%.1f", "scr")
        uric_acid                = number_or_none("Uric acid (mg/dL)", 1.0, 15.0, 0.1, ex.get("uric_acid"), "%.1f", "ua")
        albumin_creatinine_ratio = number_or_none("Urine albumin/creatinine (mg/g)", 0.0, 5000.0, 1.0, ex.get("albumin_creatinine_ratio"), "%.1f", "acr")
    with c3:
        white_blood_cells = number_or_none("WBC (10³/µL)", 1.0, 50.0, 0.1, ex.get("white_blood_cells"), "%.1f", "wbc")
        hemoglobin        = number_or_none("Hemoglobin (g/dL)", 5.0, 20.0, 0.1, ex.get("hemoglobin"), "%.1f", "hgb")
        rdw               = number_or_none("Red cell dist. width (%)", 10.0, 30.0, 0.1, ex.get("rdw"), "%.1f", "rdw")

    # ── History & Lifestyle ──────────────────────────────────────────────────
    st.subheader("📋 History & Lifestyle")
    c1, c2, c3 = st.columns(3)
    with c1:
        smoking_status          = selectbox_or_none("Smoking status", SMOKING_OPTIONS, ex.get("smoking_status"), "smk")
        physically_active       = selectbox_or_none("Moderate/vigorous exercise weekly", YESNO_OPTIONS, ex.get("physically_active"), "pa")
        hypertension_history    = selectbox_or_none("Ever told: high blood pressure", YESNO_OPTIONS, ex.get("hypertension_history"), "htn")
    with c2:
        high_cholesterol_history = selectbox_or_none("Ever told: high cholesterol", YESNO_OPTIONS, ex.get("high_cholesterol_history"), "hchol")
        diabetes_status          = selectbox_or_none("Ever told: diabetes", YESNO_OPTIONS, ex.get("diabetes_status"), "dm")
        stroke_history           = selectbox_or_none("Ever had a stroke", YESNO_OPTIONS, ex.get("stroke_history"), "stroke")
    with c3:
        family_history_chd = selectbox_or_none("Parent/sibling heart attack < 50", YESNO_OPTIONS, ex.get("family_history_chd"), "fhx")
        general_health = st.selectbox(
            "General health", list(HEALTH_OPTIONS.keys()),
            index=list(HEALTH_OPTIONS.keys()).index(ex.get("general_health")) if ex.get("general_health") in HEALTH_OPTIONS else None,
            format_func=lambda v: HEALTH_OPTIONS[v], placeholder="unknown", key="gh",
        )

    # ── Chest Symptoms ───────────────────────────────────────────────────────
    st.subheader("💔 Chest Symptoms")
    c1, c2, c3 = st.columns(3)
    with c1:
        chest_pain_type  = selectbox_or_none("Chest pain (Rose questionnaire)", CHEST_PAIN_OPTIONS, ex.get("chest_pain_type"), "cpt")
    with c2:
        severe_chest_pain = selectbox_or_none("Severe chest pain ≥ 30 min ever", YESNO_OPTIONS, ex.get("severe_chest_pain"), "scp")
    with c3:
        sob_on_exertion  = selectbox_or_none("Short of breath on exertion", YESNO_OPTIONS, ex.get("sob_on_exertion"), "sob")

    submitted = st.form_submit_button("🔍 Predict Heart Disease Risk", type="primary", use_container_width=True)

# ─── Prediction ──────────────────────────────────────────────────────────────
if submitted:
    patient = {
        "age": age, "gender": gender, "ethnicity": ethnicity,
        "education_level": education_level, "poverty_income_ratio": poverty_income_ratio,
        "bmi": bmi, "waist_cm": waist_cm, "height_cm": height_cm,
        "systolic_bp": systolic_bp, "diastolic_bp": diastolic_bp,
        "resting_heart_rate": resting_heart_rate, "total_cholesterol": total_cholesterol,
        "hdl_cholesterol": hdl_cholesterol, "hba1c": hba1c, "serum_creatinine": serum_creatinine,
        "uric_acid": uric_acid, "albumin_creatinine_ratio": albumin_creatinine_ratio,
        "white_blood_cells": white_blood_cells, "hemoglobin": hemoglobin, "rdw": rdw,
        "smoking_status": smoking_status, "physically_active": physically_active,
        "hypertension_history": hypertension_history, "high_cholesterol_history": high_cholesterol_history,
        "diabetes_status": diabetes_status, "stroke_history": stroke_history,
        "family_history_chd": family_history_chd, "general_health": general_health,
        "chest_pain_type": chest_pain_type, "severe_chest_pain": severe_chest_pain,
        "sob_on_exertion": sob_on_exertion,
    }

    # Validate age (only required field)
    if age is None:
        st.error("❌ Age is required.")
        st.stop()

    # Count knowns
    known = sum(1 for v in patient.values() if v is not None)
    if known < 5:
        st.warning(f"⚠️ Only {known} of 31 fields filled. Results may be unreliable with very few inputs.")

    with st.spinner("Running cascade (loading models on first run — up to ~30 s)…"):
        try:
            result = predict(patient, explain=True)
        except Exception as e:
            st.error(f"❌ Prediction error: {e}")
            st.stop()

    st.divider()
    st.subheader("📊 Results")

    # ── Status Banner ────────────────────────────────────────────────────────
    if result.status == "review":
        st.warning("⚠️ **Anomaly Gate triggered** — This patient profile is unusual and was withheld from scoring. "
                   "Manual clinical review is recommended.")
    elif result.positive:
        label_color = "🔴" if result.label == "High Risk" else "🟡"
        st.error(f"{label_color} **{result.label}** ({result.probability:.0%}) · {result.message}")
    else:
        st.success(f"🟢 **{result.label}** ({result.probability:.0%}) · {result.message}")

    # ── Metrics ──────────────────────────────────────────────────────────────
    if result.scored:
        col1, col2, col3 = st.columns(3)
        threshold = result.details.get("threshold", 0.2003)
        with col1:
            st.metric("Risk Probability", f"{result.probability:.1%}")
        with col2:
            st.metric("Decision Threshold", f"{threshold:.1%}")
        with col3:
            st.metric("Risk Band", result.label)

        # Progress bar coloured by risk
        st.progress(min(result.probability / 0.5, 1.0),
                    text=f"P = {result.probability:.3f} (threshold = {threshold:.4f})")

        # ── Risk Bands Reference ─────────────────────────────────────────────
        rb = result.details.get("risk_bands", {})
        if rb:
            st.caption(f"Risk bands — Low: {rb.get('low', '')} | Medium: {rb.get('medium', '')} | High: {rb.get('high', '')}")

        # ── Explanation ──────────────────────────────────────────────────────
        factors = result.explanation.get("factors", [])
        if factors:
            with st.expander("🔍 What moved this patient's risk most", expanded=True):
                st.caption(result.explanation.get("method", ""))
                rows = []
                for f in factors:
                    direction = "↑ raised risk" if f["effect"] > 0 else "↓ lowered risk"
                    rows.append({
                        "Feature": f["feature"].replace("_", " ").title(),
                        "This patient": f["value"],
                        "Typical patient": f["typical"],
                        "Effect (pp)": f"{f['effect'] * 100:+.1f}",
                        "Direction": direction,
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("No explanation factors: patient matches the typical training profile on all inputs.")

    # ── Download ─────────────────────────────────────────────────────────────
    result_dict = result.to_dict(arrays=False)
    result_dict.pop("explanation", None)   # skip numpy-heavy items for clean JSON
    result_dict["explanation_factors"] = result.explanation.get("factors", [])
    st.download_button(
        "⬇️ Download result (JSON)", data=json.dumps(result_dict, indent=2, default=str),
        file_name="heart_risk_result.json", mime="application/json",
    )
