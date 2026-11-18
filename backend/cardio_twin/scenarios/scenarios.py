"""What-if scenario domain models, simulation execution, and comparison engine.

Manages:
- Baseline reference configurations (Generic Preset vs. Patient-Specific).
- Custom what-if scenario creation with server-side validation.
- Tracking parameter deltas (absolute and relative) from reference settings.
- Direct execution of independent simulation calls via CardioSimClient.
- Safe metrics comparison (handling zero denominators and non-finite outputs).
- Structured scenario records ready for session history and serialization.
"""
from __future__ import annotations

import datetime
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from cardiosim.client import CardioSimClient
from cardiosim.models import SimMetrics, SimResponse, SimResult
from data.models import PatientRecord
from data.provenance import (
    PARAMETER_BOUNDS,
    ParameterProvenanceReport,
    ParameterStatus,
    PatientParameterResolver,
    SimulatorParameter,
    ValidationError,
    validate_parameter_value,
    validate_simulation_duration,
)


class ScenarioKind(str, Enum):
    """Classification of cardiovascular simulation scenarios."""

    GENERIC_BASELINE = "GENERIC_BASELINE"                 # Official generic CardioSim preset
    PATIENT_SPECIFIC_BASELINE = "PATIENT_SPECIFIC_BASELINE" # Provenance-validated patient baseline
    CUSTOM_WHAT_IF = "CUSTOM_WHAT_IF"                     # Hypothetical parameter variation


@dataclass(frozen=True)
class ParameterDelta:
    """Record of a parameter modification relative to a baseline reference."""

    field_name: str
    display_name: str
    unit: str
    baseline_value: float
    scenario_value: float
    absolute_change: float
    percent_change: float | None  # None if baseline is 0.0

    @property
    def has_changed(self) -> bool:
        """True if the parameter differs from baseline by more than floating point epsilon."""
        return abs(self.absolute_change) > 1e-4


@dataclass(frozen=True)
class MetricComparisonItem:
    """Side-by-side comparison for a single CardioSim ODE output metric."""

    key: str
    display_name: str
    unit: str
    description: str
    baseline_value: float | None
    scenario_value: float | None
    absolute_difference: float | None
    percent_difference: float | None  # None if baseline is 0 or unavailable
    is_defined: bool


@dataclass
class ScenarioConfiguration:
    """Validated configuration for a cardiovascular simulation scenario.

    Serializes cleanly to JSON/dict for session storage or logging.
    """

    scenario_id: str
    name: str
    kind: ScenarioKind
    preset: str
    hr: float
    contract: float
    resist: float
    compl: float
    duration: float
    parameters: dict[str, dict[str, Any]]
    disclaimer: str
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    associated_subject_id: int | None = None
    baseline_reference_id: str | None = None

    def to_client_payload(self) -> dict[str, Any]:
        """Convert configuration to exact kwargs for CardioSimClient.simulate()."""
        return {
            "preset": self.preset,
            "hr": self.hr,
            "contract": self.contract,
            "resist": self.resist,
            "compl": self.compl,
            "duration": self.duration,
        }


@dataclass
class ScenarioRecord:
    """Complete record of an executed scenario including inputs, outputs, and diffs."""

    configuration: ScenarioConfiguration
    sim_result: SimResult | None
    deltas_from_baseline: list[ParameterDelta] = field(default_factory=list)
    metric_comparisons: list[MetricComparisonItem] = field(default_factory=list)
    execution_error: str | None = None

    def to_summary_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary for UI presentation."""
        m_dict = None
        if self.sim_result and self.sim_result.metrics:
            m = self.sim_result.metrics
            m_dict = {
                "co": m.co, "sv": m.sv, "sys": m.sys, "dia": m.dia,
                "map_val": m.map_val, "pp": m.pp, "ef": m.ef, "hr": m.hr,
            }

        return {
            "scenario_id": self.configuration.scenario_id,
            "name": self.configuration.name,
            "kind": self.configuration.kind.value,
            "preset": self.configuration.preset,
            "duration": self.configuration.duration,
            "created_at": self.configuration.created_at,
            "associated_subject_id": self.configuration.associated_subject_id,
            "parameters": {
                "hr": self.configuration.hr,
                "contract": self.configuration.contract,
                "resist": self.configuration.resist,
                "compl": self.configuration.compl,
            },
            "disclaimer": self.configuration.disclaimer,
            "warnings": self.configuration.warnings,
            "metrics": m_dict,
            "has_error": self.execution_error is not None,
            "execution_error": self.execution_error,
            "deltas": [
                {
                    "field_name": d.field_name,
                    "display_name": d.display_name,
                    "unit": d.unit,
                    "baseline_value": d.baseline_value,
                    "scenario_value": d.scenario_value,
                    "absolute_change": d.absolute_change,
                    "percent_change": d.percent_change,
                    "has_changed": d.has_changed,
                }
                for d in self.deltas_from_baseline
            ],
            "metric_comparisons": [
                {
                    "key": item.key,
                    "display_name": item.display_name,
                    "unit": item.unit,
                    "description": item.description,
                    "baseline_value": item.baseline_value,
                    "scenario_value": item.scenario_value,
                    "absolute_difference": item.absolute_difference,
                    "percent_difference": item.percent_difference,
                    "is_defined": item.is_defined,
                }
                for item in self.metric_comparisons
            ],
        }


# Standard documentation for simulator output metrics
OUTPUT_METRIC_DOCS = [
    ("co", "Cardiac Output", "L/min", "Volumetric flow rate of blood pumped by the ventricle per minute."),
    ("sv", "Stroke Volume", "mL", "Volume of blood ejected from the left ventricle per beat."),
    ("sys", "Systolic Pressure", "mmHg", "Peak arterial pressure during ventricular systole."),
    ("dia", "Diastolic Pressure", "mmHg", "Minimum arterial pressure during ventricular diastole."),
    ("map_val", "Mean Arterial Pressure", "mmHg", "Time-averaged systemic arterial pressure over the cardiac cycle."),
    ("pp", "Pulse Pressure", "mmHg", "Difference between systolic and diastolic arterial pressures."),
    ("ef", "Ejection Fraction", "%", "Percentage of end-diastolic ventricular blood volume ejected per beat."),
    ("hr", "Heart Rate", "bpm", "Frequency of the cardiac cycle (beats per minute)."),
]


def compute_metric_comparisons(
    baseline_metrics: SimMetrics | None,
    scenario_metrics: SimMetrics | None,
) -> list[MetricComparisonItem]:
    """Compare baseline and scenario outputs safely without zero division or fabricated numbers."""
    comparisons: list[MetricComparisonItem] = []

    for key, name, unit, desc in OUTPUT_METRIC_DOCS:
        b_val = getattr(baseline_metrics, key, None) if baseline_metrics else None
        s_val = getattr(scenario_metrics, key, None) if scenario_metrics else None

        if b_val is None or s_val is None:
            comparisons.append(
                MetricComparisonItem(
                    key=key,
                    display_name=name,
                    unit=unit,
                    description=desc,
                    baseline_value=b_val,
                    scenario_value=s_val,
                    absolute_difference=None,
                    percent_difference=None,
                    is_defined=False,
                )
            )
            continue

        b_float = float(b_val)
        s_float = float(s_val)

        if not (math.isfinite(b_float) and math.isfinite(s_float)):
            comparisons.append(
                MetricComparisonItem(
                    key=key,
                    display_name=name,
                    unit=unit,
                    description=desc,
                    baseline_value=b_float,
                    scenario_value=s_float,
                    absolute_difference=None,
                    percent_difference=None,
                    is_defined=False,
                )
            )
            continue

        abs_diff = s_float - b_float

        # Zero denominator check: percent change is undefined if baseline is 0.0
        pct_diff: float | None = None
        if abs(b_float) > 1e-9:
            pct_diff = (abs_diff / b_float) * 100.0

        comparisons.append(
            MetricComparisonItem(
                key=key,
                display_name=name,
                unit=unit,
                description=desc,
                baseline_value=b_float,
                scenario_value=s_float,
                absolute_difference=abs_diff,
                percent_difference=pct_diff,
                is_defined=True,
            )
        )

    return comparisons


class ScenarioEngine:
    """Orchestrates what-if scenario creation, validation, simulation, and comparison."""

    def __init__(self, client: CardioSimClient | None = None) -> None:
        self.client = client or CardioSimClient()

    def build_generic_baseline(
        self,
        preset_name: str,
        presets_dict: dict[str, Any],
        duration: float = 6.0,
        patient: PatientRecord | None = None,
    ) -> ScenarioConfiguration:
        """Create a validated generic reference baseline configuration."""
        if preset_name not in presets_dict:
            raise ValidationError(f"Preset {preset_name!r} not found in available CardioSim presets.")

        pinfo = presets_dict[preset_name]
        d = validate_simulation_duration(duration)

        hr = validate_parameter_value("hr", pinfo.hr)
        contract = validate_parameter_value("contract", pinfo.contract)
        resist = validate_parameter_value("resist", pinfo.resist)
        compl = validate_parameter_value("compl", pinfo.compl)

        params_map = {
            "hr": {
                "value": hr, "unit": "bpm", "status": ParameterStatus.ASSUMED.value,
                "display_name": "Heart Rate", "source": f"Preset '{preset_name}' default",
            },
            "contract": {
                "value": contract, "unit": "%", "status": ParameterStatus.ASSUMED.value,
                "display_name": "Contractility", "source": f"Preset '{preset_name}' default",
            },
            "resist": {
                "value": resist, "unit": "mmHg·s/mL", "status": ParameterStatus.ASSUMED.value,
                "display_name": "Resistance", "source": f"Preset '{preset_name}' default",
            },
            "compl": {
                "value": compl, "unit": "mL/mmHg", "status": ParameterStatus.ASSUMED.value,
                "display_name": "Compliance", "source": f"Preset '{preset_name}' default",
            },
        }

        disclaimer = (
            f"Generic Reference Baseline: '{preset_name}'. "
            "Parameters are population model defaults and are NOT derived from patient measurements. "
            "This configuration establishes a mathematical reference, not a personalized clinical twin."
        )

        return ScenarioConfiguration(
            scenario_id=f"baseline_{preset_name.lower().replace(' ', '_')}",
            name=f"Reference Baseline ({preset_name})",
            kind=ScenarioKind.GENERIC_BASELINE,
            preset=preset_name,
            hr=hr,
            contract=contract,
            resist=resist,
            compl=compl,
            duration=d,
            parameters=params_map,
            disclaimer=disclaimer,
            warnings=[
                "Hypothetical reference scenario: clinical observations are not used as simulation parameters."
            ],
            associated_subject_id=patient.subject_id if patient else None,
        )

    def create_custom_scenario(
        self,
        name: str,
        baseline_config: ScenarioConfiguration,
        hr: Any,
        contract: Any,
        resist: Any,
        compl: Any,
        duration: Any = 6.0,
        patient: PatientRecord | None = None,
    ) -> tuple[ScenarioConfiguration, list[ParameterDelta]]:
        """Validate and construct a hypothetical custom scenario branching from baseline."""
        scenario_name = str(name).strip() if name else "Custom What-if Scenario"
        d = validate_simulation_duration(duration)

        v_hr = validate_parameter_value("hr", hr)
        v_contract = validate_parameter_value("contract", contract)
        v_resist = validate_parameter_value("resist", resist)
        v_compl = validate_parameter_value("compl", compl)

        # Compute parameter deltas from baseline
        deltas: list[ParameterDelta] = []
        param_pairs = [
            ("hr", "Heart Rate", "bpm", baseline_config.hr, v_hr),
            ("contract", "Contractility", "%", baseline_config.contract, v_contract),
            ("resist", "Resistance", "mmHg·s/mL", baseline_config.resist, v_resist),
            ("compl", "Compliance", "mL/mmHg", baseline_config.compl, v_compl),
        ]

        params_map = {}
        changed_descriptions = []

        for field_name, label, unit, b_val, s_val in param_pairs:
            diff = s_val - b_val
            pct = (diff / b_val * 100.0) if abs(b_val) > 1e-9 else None
            delta = ParameterDelta(
                field_name=field_name,
                display_name=label,
                unit=unit,
                baseline_value=b_val,
                scenario_value=s_val,
                absolute_change=diff,
                percent_change=pct,
            )
            deltas.append(delta)

            if delta.has_changed:
                sign = "+" if diff > 0 else ""
                changed_descriptions.append(f"{label} {sign}{diff:.2f} {unit}")

            params_map[field_name] = {
                "value": s_val,
                "unit": unit,
                "status": ParameterStatus.ASSUMED.value,  # User inputs are ALWAYS assumed
                "display_name": label,
                "source": "Interactive What-if Adjustment",
                "notes": f"Branch from {baseline_config.name}",
            }

        disclaimer = (
            f"Interactive What-if Scenario: '{scenario_name}'. "
            "All adjusted values are hypothetical assumptions for research exploration. "
            "They do NOT represent measured clinical changes or prognostic predictions."
        )

        warnings = [
            "Mathematical ODE simulation only.",
            "Changes are researcher-specified hypotheses, not clinical treatment effects.",
        ]
        if changed_descriptions:
            warnings.append(f"Modified parameters: {', '.join(changed_descriptions)}.")

        scenario_id = f"scenario_{datetime.datetime.now().strftime('%H%M%S%f')}"
        config = ScenarioConfiguration(
            scenario_id=scenario_id,
            name=scenario_name,
            kind=ScenarioKind.CUSTOM_WHAT_IF,
            preset=baseline_config.preset,
            hr=v_hr,
            contract=v_contract,
            resist=v_resist,
            compl=v_compl,
            duration=d,
            parameters=params_map,
            disclaimer=disclaimer,
            warnings=warnings,
            associated_subject_id=patient.subject_id if patient else None,
            baseline_reference_id=baseline_config.scenario_id,
        )

        return config, deltas

    def run_scenario(
        self,
        config: ScenarioConfiguration,
        baseline_record: ScenarioRecord | None = None,
    ) -> ScenarioRecord:
        """Execute a scenario via CardioSimClient as an independent simulation call."""
        payload = config.to_client_payload()
        try:
            # Independent API call - never passes patient observations, demographics, or IDs
            response: SimResponse = self.client.simulate(**payload)
            primary_result = response.primary

            # If a baseline record is provided, compute metric comparisons and parameter deltas
            comparisons: list[MetricComparisonItem] = []
            deltas: list[ParameterDelta] = []

            if baseline_record and baseline_record.sim_result:
                comparisons = compute_metric_comparisons(
                    baseline_record.sim_result.metrics,
                    primary_result.metrics,
                )
                b_cfg = baseline_record.configuration
                param_pairs = [
                    ("hr", "Heart Rate", "bpm", b_cfg.hr, config.hr),
                    ("contract", "Contractility", "%", b_cfg.contract, config.contract),
                    ("resist", "Resistance", "mmHg·s/mL", b_cfg.resist, config.resist),
                    ("compl", "Compliance", "mL/mmHg", b_cfg.compl, config.compl),
                ]
                for fn, lbl, u, b_v, s_v in param_pairs:
                    diff = s_v - b_v
                    pct = (diff / b_v * 100.0) if abs(b_v) > 1e-9 else None
                    deltas.append(
                        ParameterDelta(
                            field_name=fn,
                            display_name=lbl,
                            unit=u,
                            baseline_value=b_v,
                            scenario_value=s_v,
                            absolute_change=diff,
                            percent_change=pct,
                        )
                    )

            return ScenarioRecord(
                configuration=config,
                sim_result=primary_result,
                deltas_from_baseline=deltas,
                metric_comparisons=comparisons,
                execution_error=None,
            )
        except Exception as exc:
            return ScenarioRecord(
                configuration=config,
                sim_result=None,
                deltas_from_baseline=[],
                metric_comparisons=[],
                execution_error=str(exc),
            )

