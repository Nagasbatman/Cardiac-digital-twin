"""UI presenter layer: prepares view models, trend charts, and reports.

Keeps templates and routes clean and decoupled from raw data processing.
Enforces all research and scientific boundaries:
- Preserves raw clinical observations without modification or smoothing.
- Never interpolates or imputes missing values.
- Never plots incompatible or unknown units on a shared numeric axis.
- Labels all generic preset simulations as hypothetical scenarios.
- Generates clean, accessible, dependency-free SVG charts with companion tables.
"""
from __future__ import annotations

import html
from collections import defaultdict
from typing import Any

from markupsafe import Markup

from cardiosim.models import SimMetrics, SimResponse, SimResult
from data.eligibility import evaluate_simulation_eligibility
from data.models import ClinicalObservation, PatientRecord

# Standard CardioSim metric documentation (names, units, descriptions)
DOCUMENTED_SIM_METRICS = [
    ("co", "Cardiac Output", "L/min", "Volumetric flow rate of blood pumped by the ventricle per minute."),
    ("sv", "Stroke Volume", "mL", "Volume of blood ejected from the left ventricle per beat."),
    ("sys", "Systolic Pressure", "mmHg", "Peak arterial pressure during ventricular systole."),
    ("dia", "Diastolic Pressure", "mmHg", "Minimum arterial pressure during ventricular diastole."),
    ("map_val", "Mean Arterial", "mmHg", "Time-averaged systemic arterial pressure over the cardiac cycle."),
    ("pp", "Pulse Pressure", "mmHg", "Difference between systolic and diastolic arterial pressures."),
    ("ef", "Ejection Fraction", "%", "Percentage of end-diastolic ventricular blood volume ejected per beat."),
    ("hr", "Heart Rate", "bpm", "Frequency of the cardiac cycle (beats per minute)."),
]

CATEGORY_DEFINITIONS = {
    "Blood Pressure": [
        "systolic_blood_pressure",
        "diastolic_blood_pressure",
    ],
    "Cardiac Troponin": [
        "troponin_t",
        "troponin_i",
    ],
    "Lipid Profile": [
        "total_cholesterol",
        "hdl_cholesterol",
        "ldl_cholesterol_calculated",
        "ldl_cholesterol_measured",
        "triglycerides",
    ],
    "Glycemic Context": [
        "hba1c",
    ],
    "Renal Context": [
        "creatinine",
    ],
}


def _format_display_name(raw_name: str) -> str:
    """Format snake_case measurement name for clean human reading."""
    replacements = {
        "systolic_blood_pressure": "Systolic Blood Pressure",
        "diastolic_blood_pressure": "Diastolic Blood Pressure",
        "troponin_t": "Troponin T",
        "troponin_i": "Troponin I",
        "total_cholesterol": "Total Cholesterol",
        "hdl_cholesterol": "HDL Cholesterol",
        "ldl_cholesterol_calculated": "LDL Cholesterol (Calculated)",
        "ldl_cholesterol_measured": "LDL Cholesterol (Measured)",
        "triglycerides": "Triglycerides",
        "hba1c": "Hemoglobin A1c (HbA1c)",
        "creatinine": "Serum Creatinine",
    }
    return replacements.get(raw_name, raw_name.replace("_", " ").title())


def build_patient_summary(patient: PatientRecord | None) -> dict[str, Any]:
    """Generate demographic and coverage summary for the selected patient."""
    if patient is None:
        return {"is_loaded": False}

    obs = patient.observations
    total_obs = len(obs)

    # Dates
    distinct_dates = {o.event_date for o in obs if o.event_date}
    
    # Admissions represented
    admissions_represented = {o.hadm_id for o in obs if o.hadm_id is not None}

    # Data quality flags
    missing_values = sum(1 for o in obs if o.is_missing_value)
    unrecorded_units = sum(1 for o in obs if o.is_missing_unit)
    requires_review = sum(1 for o in obs if o.requires_review)

    # Category coverage
    present_names = {o.measurement_name for o in obs}
    categories_present = []
    categories_absent = []

    for cat_name, cat_fields in CATEGORY_DEFINITIONS.items():
        if any(f in present_names for f in cat_fields):
            categories_present.append(cat_name)
        else:
            categories_absent.append(cat_name)

    # Demographics (Do NOT include date of death)
    demographics = {
        "gender": patient.demographics.gender or "Unknown",
        "anchor_age": (
            str(patient.demographics.anchor_age)
            if patient.demographics.anchor_age is not None
            else "Unknown"
        ),
        "anchor_year_group": patient.demographics.anchor_year_group or "Unknown",
    }

    # Eligibility evaluation
    eligibility = evaluate_simulation_eligibility(patient)

    return {
        "is_loaded": True,
        "subject_id": patient.subject_id,
        "demographics": demographics,
        "total_observations": total_obs,
        "distinct_dates_count": len(distinct_dates),
        "admissions_represented_count": len(admissions_represented),
        "missing_values_count": missing_values,
        "unrecorded_units_count": unrecorded_units,
        "requires_review_count": requires_review,
        "categories_present": categories_present,
        "categories_absent": categories_absent,
        "is_eligible_for_patient_specific": eligibility.is_eligible_for_patient_specific,
        "ineligible_reason": eligibility.reason,
    }


def _generate_svg_chart(
    series_list: list[dict[str, Any]],
    date_labels: list[str],
    unit_label: str,
    chart_id: str,
    width: int = 580,
    height: int = 220,
) -> str:
    """Generate clean, accessible, dependency-free SVG line/scatter markup."""
    # Find global min and max among all series points
    all_vals: list[float] = []
    for s in series_list:
        for pt in s["points"]:
            all_vals.append(pt["y"])

    if not all_vals:
        return ""

    min_y = min(all_vals)
    max_y = max(all_vals)

    # Padding on y
    if min_y == max_y:
        min_y = max(0.0, min_y - 10.0)
        max_y = max_y + 10.0
    else:
        pad = (max_y - min_y) * 0.15
        min_y = max(0.0, min_y - pad)
        max_y = max_y + pad

    margin_left = 60
    margin_right = 30
    margin_top = 25
    margin_bottom = 45

    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    num_x = len(date_labels)

    def x_coord(idx: int) -> float:
        if num_x <= 1:
            return margin_left + plot_w / 2.0
        return margin_left + (idx / (num_x - 1)) * plot_w

    def y_coord(val: float) -> float:
        if max_y == min_y:
            return margin_top + plot_h / 2.0
        ratio = (val - min_y) / (max_y - min_y)
        return margin_top + plot_h - (ratio * plot_h)

    elements: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" class="trend-svg" role="img" aria-label="Clinical trend chart in {html.escape(unit_label)}">'
    ]

    # Grid lines & Y ticks (3 levels)
    for i in range(4):
        val = min_y + (i / 3.0) * (max_y - min_y)
        y = y_coord(val)
        elements.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#334155" stroke-dasharray="3,3" stroke-width="1" />'
        )
        elements.append(
            f'<text x="{margin_left - 8}" y="{y + 4:.1f}" fill="#94a3b8" font-size="10" text-anchor="end">{val:.1f}</text>'
        )

    # X axis line
    baseline_y = margin_top + plot_h
    elements.append(
        f'<line x1="{margin_left}" y1="{baseline_y:.1f}" x2="{width - margin_right}" y2="{baseline_y:.1f}" stroke="#64748b" stroke-width="1.5" />'
    )

    # X axis date ticks (show up to 5 dates evenly spaced)
    step = max(1, num_x // 4)
    tick_indices = list(range(0, num_x, step))
    if (num_x - 1) not in tick_indices:
        tick_indices.append(num_x - 1)

    for idx in tick_indices:
        x = x_coord(idx)
        lbl = date_labels[idx]
        # Shorten label if needed
        short_lbl = lbl[-5:] if len(lbl) >= 5 else lbl
        elements.append(
            f'<line x1="{x:.1f}" y1="{baseline_y}" x2="{x:.1f}" y2="{baseline_y + 4}" stroke="#64748b" stroke-width="1" />'
        )
        elements.append(
            f'<text x="{x:.1f}" y="{baseline_y + 16}" fill="#94a3b8" font-size="10" text-anchor="middle">{html.escape(short_lbl)}</text>'
        )

    # Plot lines and circles for each series
    for s in series_list:
        color = s["color"]
        pts = sorted(s["points"], key=lambda p: p["x_idx"])

        # If 2 or more points, draw line
        if len(pts) >= 2:
            path_d_parts = []
            for j, p in enumerate(pts):
                cx = x_coord(p["x_idx"])
                cy = y_coord(p["y"])
                cmd = "M" if j == 0 else "L"
                path_d_parts.append(f"{cmd} {cx:.1f} {cy:.1f}")
            path_d = " ".join(path_d_parts)
            elements.append(
                f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
            )

        # Draw circle markers for every point
        for p in pts:
            cx = x_coord(p["x_idx"])
            cy = y_coord(p["y"])
            tooltip = f"{s['name']}: {p['y']} {unit_label} on {p['date']}"
            elements.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="{color}" stroke="#0f172a" stroke-width="1.5">'
                f'<title>{html.escape(tooltip)}</title></circle>'
            )

    elements.append("</svg>")
    return "".join(elements)


def build_clinical_trends(patient: PatientRecord | None) -> list[dict[str, Any]]:
    """Build honest, non-interpolated clinical trend charts and tables."""
    if patient is None:
        return []

    trends: list[dict[str, Any]] = []

    # 1. Blood Pressure Trend
    bp_obs = patient.get_observations("systolic_blood_pressure") + patient.get_observations("diastolic_blood_pressure")
    bp_dated = [o for o in bp_obs if o.event_date and o.value_numeric is not None]
    
    # Collect unique dates sorted
    all_dates = sorted({o.event_date for o in bp_dated if o.event_date})
    date_map = {d: i for i, d in enumerate(all_dates)}

    sbp_pts = []
    dbp_pts = []
    bp_rows = []

    for o in sorted(bp_obs, key=lambda x: (x.event_date or "", x.event_time or "")):
        row = {
            "name": _format_display_name(o.measurement_name),
            "value": o.value_numeric,
            "unit": o.measurement_unit or "Unrecorded",
            "date": o.event_date or "Undated",
            "source": o.source.upper(),
            "status": o.value_review_status,
        }
        bp_rows.append(row)

        if o.event_date and o.value_numeric is not None:
            pt = {
                "x_idx": date_map[o.event_date],
                "y": o.value_numeric,
                "date": o.event_date,
            }
            if o.measurement_name == "systolic_blood_pressure":
                sbp_pts.append(pt)
            else:
                dbp_pts.append(pt)

    bp_svg = ""
    has_bp_chart = len(all_dates) > 0 and (len(sbp_pts) > 0 or len(dbp_pts) > 0)
    if has_bp_chart:
        bp_series = []
        if sbp_pts:
            bp_series.append({"name": "Systolic BP", "color": "#38bdf8", "points": sbp_pts})
        if dbp_pts:
            bp_series.append({"name": "Diastolic BP", "color": "#06b6d4", "points": dbp_pts})
        bp_svg = _generate_svg_chart(bp_series, all_dates, "Unrecorded unit (OMR)", "bp-chart")

    trends.append({
        "id": "bp",
        "title": "Blood Pressure (Systolic & Diastolic)",
        "unit": "Unrecorded unit in source",
        "unit_caveat": "Outpatient OMR source records lack documented measurement units; plotted on relative scale without assuming mmHg.",
        "has_chart": has_bp_chart,
        "empty_reason": "No dated blood pressure observations recorded for this patient.",
        "svg": Markup(bp_svg) if bp_svg else "",
        "rows": bp_rows,
        "series_legend": [
            {"name": "Systolic BP", "color": "#38bdf8"},
            {"name": "Diastolic BP", "color": "#06b6d4"},
        ],
    })

    # 2. Cardiac Troponin (Troponin T and Troponin I distinct)
    trop_obs = patient.get_observations("troponin_t") + patient.get_observations("troponin_i")
    trop_dated = [o for o in trop_obs if o.event_date and o.value_numeric is not None]
    t_dates = sorted({o.event_date for o in trop_dated if o.event_date})
    t_date_map = {d: i for i, d in enumerate(t_dates)}

    trop_t_pts = []
    trop_i_pts = []
    trop_rows = []

    for o in sorted(trop_obs, key=lambda x: (x.event_date or "", x.event_time or "")):
        trop_rows.append({
            "name": _format_display_name(o.measurement_name),
            "value": o.value_numeric,
            "unit": o.measurement_unit or "Unrecorded",
            "date": o.event_date or "Undated",
            "source": o.source.upper(),
            "status": o.value_review_status,
        })
        if o.event_date and o.value_numeric is not None:
            pt = {"x_idx": t_date_map[o.event_date], "y": o.value_numeric, "date": o.event_date}
            if o.measurement_name == "troponin_t":
                trop_t_pts.append(pt)
            else:
                trop_i_pts.append(pt)

    trop_svg = ""
    has_trop_chart = len(t_dates) > 0 and (len(trop_t_pts) > 0 or len(trop_i_pts) > 0)
    if has_trop_chart:
        trop_series = []
        if trop_t_pts:
            trop_series.append({"name": "Troponin T", "color": "#f43f5e", "points": trop_t_pts})
        if trop_i_pts:
            trop_series.append({"name": "Troponin I", "color": "#e11d48", "points": trop_i_pts})
        trop_svg = _generate_svg_chart(trop_series, t_dates, "ng/mL", "trop-chart")

    trends.append({
        "id": "troponin",
        "title": "Cardiac Troponin (T & I distinct)",
        "unit": "ng/mL",
        "unit_caveat": "Lab measurements recorded in ng/mL. Troponin T and Troponin I use distinct diagnostic assays and are tracked separately.",
        "has_chart": has_trop_chart,
        "empty_reason": "No dated troponin observations recorded for this patient.",
        "svg": Markup(trop_svg) if trop_svg else "",
        "rows": trop_rows,
        "series_legend": [
            {"name": "Troponin T", "color": "#f43f5e"},
            {"name": "Troponin I", "color": "#e11d48"},
        ],
    })

    # 3. Lipid Profile
    lipid_names = [
        "total_cholesterol",
        "hdl_cholesterol",
        "ldl_cholesterol_calculated",
        "ldl_cholesterol_measured",
        "triglycerides",
    ]
    lipid_obs = []
    for ln in lipid_names:
        lipid_obs.extend(patient.get_observations(ln))

    lipid_dated = [o for o in lipid_obs if o.event_date and o.value_numeric is not None]
    l_dates = sorted({o.event_date for o in lipid_dated if o.event_date})
    l_date_map = {d: i for i, d in enumerate(l_dates)}

    lipid_series_dict = defaultdict(list)
    lipid_rows = []

    for o in sorted(lipid_obs, key=lambda x: (x.event_date or "", x.event_time or "")):
        lipid_rows.append({
            "name": _format_display_name(o.measurement_name),
            "value": o.value_numeric,
            "unit": o.measurement_unit or "mg/dL",
            "date": o.event_date or "Undated",
            "source": o.source.upper(),
            "status": o.value_review_status,
        })
        if o.event_date and o.value_numeric is not None:
            pt = {"x_idx": l_date_map[o.event_date], "y": o.value_numeric, "date": o.event_date}
            lipid_series_dict[o.measurement_name].append(pt)

    lipid_colors = {
        "total_cholesterol": "#a855f7",
        "hdl_cholesterol": "#10b981",
        "ldl_cholesterol_calculated": "#f59e0b",
        "ldl_cholesterol_measured": "#d97706",
        "triglycerides": "#ec4899",
    }
    lipid_series = []
    for ln in lipid_names:
        if lipid_series_dict[ln]:
            lipid_series.append({
                "name": _format_display_name(ln),
                "color": lipid_colors.get(ln, "#94a3b8"),
                "points": lipid_series_dict[ln],
            })

    lipid_svg = ""
    has_lipid_chart = len(l_dates) > 0 and len(lipid_series) > 0
    if has_lipid_chart:
        lipid_svg = _generate_svg_chart(lipid_series, l_dates, "mg/dL", "lipid-chart")

    trends.append({
        "id": "lipids",
        "title": "Lipid Profile (Cholesterol, HDL, LDL, Triglycerides)",
        "unit": "mg/dL",
        "unit_caveat": "All lipid subfractions recorded in mg/dL. Calculated and measured LDL are kept distinct.",
        "has_chart": has_lipid_chart,
        "empty_reason": "No dated lipid panel observations recorded for this patient.",
        "svg": Markup(lipid_svg) if lipid_svg else "",
        "rows": lipid_rows,
        "series_legend": [
            {"name": _format_display_name(ln), "color": lipid_colors[ln]}
            for ln in lipid_names
            if lipid_series_dict[ln]
        ],
    })

    # 4. Metabolic & Renal Context (HbA1c & Creatinine)
    meta_obs = patient.get_observations("hba1c") + patient.get_observations("creatinine")
    meta_rows = [
        {
            "name": _format_display_name(o.measurement_name),
            "value": o.value_numeric,
            "unit": o.measurement_unit or "—",
            "date": o.event_date or "Undated",
            "source": o.source.upper(),
            "status": o.value_review_status,
        }
        for o in sorted(meta_obs, key=lambda x: (x.event_date or "", x.event_time or ""))
    ]

    # HbA1c chart
    hba1c_obs = [o for o in patient.get_observations("hba1c") if o.event_date and o.value_numeric is not None]
    h_dates = sorted({o.event_date for o in hba1c_obs if o.event_date})
    h_date_map = {d: i for i, d in enumerate(h_dates)}
    h_pts = [{"x_idx": h_date_map[o.event_date], "y": o.value_numeric, "date": o.event_date} for o in hba1c_obs]
    hba1c_svg = _generate_svg_chart([{"name": "HbA1c", "color": "#0ea5e9", "points": h_pts}], h_dates, "%", "hba1c-chart") if h_pts else ""

    # Creatinine chart
    creat_obs = [o for o in patient.get_observations("creatinine") if o.event_date and o.value_numeric is not None]
    c_dates = sorted({o.event_date for o in creat_obs if o.event_date})
    c_date_map = {d: i for i, d in enumerate(c_dates)}
    c_pts = [{"x_idx": c_date_map[o.event_date], "y": o.value_numeric, "date": o.event_date} for o in creat_obs]
    creat_svg = _generate_svg_chart([{"name": "Creatinine", "color": "#6366f1", "points": c_pts}], c_dates, "mg/dL", "creat-chart") if c_pts else ""

    trends.append({
        "id": "metabolic",
        "title": "Metabolic & Renal Context (HbA1c & Creatinine)",
        "unit": "HbA1c (%) | Creatinine (mg/dL)",
        "unit_caveat": "HbA1c and creatinine use different units (% and mg/dL) and are plotted on separate distinct axes to avoid misleading scaling.",
        "has_chart": bool(hba1c_svg or creat_svg),
        "empty_reason": "No dated metabolic/renal observations recorded for this patient.",
        "hba1c_svg": Markup(hba1c_svg) if hba1c_svg else "",
        "creat_svg": Markup(creat_svg) if creat_svg else "",
        "rows": meta_rows,
    })

    return trends


def build_cardiovascular_analysis(patient: PatientRecord | None) -> list[dict[str, Any]]:
    """Organize patient observations into structured clinical review cards."""
    if patient is None:
        return []

    analysis_cards: list[dict[str, Any]] = []

    for cat_name, field_names in CATEGORY_DEFINITIONS.items():
        matched_obs: list[ClinicalObservation] = []
        for fn in field_names:
            matched_obs.extend(patient.get_observations(fn))

        valid_vals = [o.value_numeric for o in matched_obs if o.value_numeric is not None]
        unrecorded_units_count = sum(1 for o in matched_obs if o.is_missing_unit)
        review_count = sum(1 for o in matched_obs if o.requires_review)

        latest_obs = None
        if matched_obs:
            latest_obs = max(matched_obs, key=lambda o: (o.event_date or "", o.event_time or ""))

        analysis_cards.append({
            "category": cat_name,
            "observation_count": len(matched_obs),
            "valid_count": len(valid_vals),
            "latest_reading": (
                f"{latest_obs.value_numeric} {latest_obs.measurement_unit or '(Unrecorded unit)'}"
                if latest_obs and latest_obs.value_numeric is not None
                else "No numeric value recorded"
            ),
            "latest_date": latest_obs.event_date if latest_obs and latest_obs.event_date else "Undated",
            "range": (
                f"{min(valid_vals):.1f} – {max(valid_vals):.1f}"
                if valid_vals
                else "N/A"
            ),
            "unrecorded_units_count": unrecorded_units_count,
            "requires_review_count": review_count,
            "fields": [_format_display_name(fn) for fn in field_names],
        })

    return analysis_cards


def build_comparison_metrics(
    sim_response: SimResponse | None,
    primary_preset: str,
    compare_preset: str | None,
    presets_dict: dict[str, Any],
) -> dict[str, Any]:
    """Build side-by-side comparison tables when a comparison preset was run."""
    if sim_response is None or sim_response.comparison is None or not compare_preset:
        return {
            "has_comparison": False,
            "message": "Select both a Primary Preset and Comparison Preset in the form to generate a dual-scenario comparison.",
        }

    m1 = sim_response.primary.metrics
    m2 = sim_response.comparison.metrics

    metrics_comparison = []
    for key, name, unit, desc in DOCUMENTED_SIM_METRICS:
        val1 = getattr(m1, key, 0.0)
        val2 = getattr(m2, key, 0.0)
        diff = val2 - val1
        metrics_comparison.append({
            "key": key,
            "name": name,
            "unit": unit,
            "description": desc,
            "val1": f"{val1:.2f}" if key in ("co", "ef") else f"{val1:.1f}",
            "val2": f"{val2:.2f}" if key in ("co", "ef") else f"{val2:.1f}",
            "diff": f"{'+' if diff > 0 else ''}{diff:.2f}" if key in ("co", "ef") else f"{'+' if diff > 0 else ''}{diff:.1f}",
        })

    p1_info = presets_dict.get(primary_preset)
    p2_info = presets_dict.get(compare_preset)

    params_comparison = [
        ("Heart Rate (hr)", "bpm", getattr(p1_info, "hr", "—"), getattr(p2_info, "hr", "—")),
        ("Contractility (contract)", "%", getattr(p1_info, "contract", "—"), getattr(p2_info, "contract", "—")),
        ("Resistance (resist)", "mmHg·s/mL", getattr(p1_info, "resist", "—"), getattr(p2_info, "resist", "—")),
        ("Compliance (compl)", "mL/mmHg", getattr(p1_info, "compl", "—"), getattr(p2_info, "compl", "—")),
    ]

    return {
        "has_comparison": True,
        "primary_preset": primary_preset,
        "compare_preset": compare_preset,
        "metrics_rows": metrics_comparison,
        "params_rows": params_comparison,
        "disclaimer": (
            f"Dual-Scenario Comparison: Compares generic preset '{primary_preset}' against generic preset '{compare_preset}'. "
            "Both are mathematical ODE model simulations and are NOT derived from this patient's clinical measurements. "
            "'Baseline' refers strictly to the selected model preset, not the patient's biological state."
        ),
    }



# ---------------------------------------------------------------------------
# Phase 4 Scenario & Provenance View Model Builders
# ---------------------------------------------------------------------------

def build_provenance_view(patient: PatientRecord | None) -> dict[str, Any]:
    """Build view model for parameter provenance cards and readiness breakdown."""
    from data.provenance import PatientParameterResolver
    report = PatientParameterResolver.resolve_patient_parameters(patient)
    return {
        "is_patient_specific_supported": report.is_patient_specific_supported,
        "readiness_summary": report.readiness_summary,
        "missing_parameters": report.missing_parameters,
        "parameters": [
            {
                "field_name": p.field_name,
                "display_name": p.display_name,
                "value": p.value if p.value is not None else "Unavailable",
                "unit": p.unit,
                "status": p.status.value,
                "source": p.source_reference,
                "notes": p.notes,
                "is_valid": p.is_valid,
            }
            for p in report.parameters.values()
        ],
        "unsupported_mappings": report.unsupported_mappings_explanation,
        "assumptions": report.assumptions_summary,
    }


def build_scenario_comparison_view(
    baseline_record: Any | None,
    current_scenario_record: Any | None,
    all_scenarios: list[Any],
) -> dict[str, Any]:
    """Build side-by-side comparison for what-if scenarios against baseline."""
    if not current_scenario_record:
        return {
            "has_scenario": False,
            "message": "No what-if scenario executed yet. Create and run a hypothetical scenario to compare against baseline.",
            "all_scenarios": [s.to_summary_dict() for s in all_scenarios],
        }

    c_dict = current_scenario_record.to_summary_dict()
    b_dict = baseline_record.to_summary_dict() if baseline_record else None

    return {
        "has_scenario": True,
        "current_scenario": c_dict,
        "baseline_scenario": b_dict,
        "deltas": c_dict.get("deltas", []),
        "metric_comparisons": c_dict.get("metric_comparisons", []),
        "all_scenarios": [s.to_summary_dict() for s in all_scenarios],
        "disclaimer": c_dict.get("disclaimer", ""),
        "warnings": c_dict.get("warnings", []),
    }
