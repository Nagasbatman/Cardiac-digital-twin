/**
 * TypeScript Interfaces for Module III: Cardiovascular Digital Twin & CardioSim.
 */

export interface Demographics {
  gender: string;
  anchor_age: string;
  anchor_year_group: string;
}

export interface PatientSummary {
  is_loaded: boolean;
  subject_id: number;
  demographics: Demographics;
  total_observations: number;
  distinct_dates_count: number;
  admissions_represented_count: number;
  missing_values_count: number;
  unrecorded_units_count: number;
  requires_review_count: number;
  categories_present: string[];
  categories_absent: string[];
  is_eligible_for_patient_specific: boolean;
  ineligible_reason: string;
}

export interface SampleProfile {
  subject_id: number;
  gender: string;
  anchor_age: number;
  anchor_year_group: string;
  observation_count: number;
  distinct_dates: number;
}

export interface PatientListResponse {
  total_patients: number;
  filtered_count: number;
  limit: number;
  offset: number;
  patient_ids: number[];
  sample_profiles: SampleProfile[];
}

export interface ClinicalObservation {
  measurement_name: string;
  display_name: string;
  value_numeric: number | null;
  measurement_unit: string | null;
  event_date: string | null;
  event_time: string | null;
  source: string;
  source_label: string | null;
  hadm_id: number | null;
  value_review_status: string;
  usable_for_patient_analysis: boolean;
}

export interface ObservationsResponse {
  total: number;
  limit: number;
  offset: number;
  observations: ClinicalObservation[];
}

export interface TrendRow {
  date: string;
  display_name: string;
  field_name: string;
  value_str: string;
  unit: string;
  source_label: string;
  hadm_id: string;
}

export interface TrendCategory {
  category: string;
  unit: string;
  data_table: TrendRow[];
  svg_chart: string;
}

export interface CategoryAnalysis {
  category: string;
  fields: string[];
  observation_count: number;
  valid_count: number;
  unrecorded_units_count: number;
  requires_review_count: number;
  latest_reading: string;
  latest_date: string;
  range: string;
}

export interface ProvenanceParameter {
  field_name: string;
  display_name: string;
  value: string | number;
  unit: string;
  status: "MEASURED" | "ESTIMATED" | "ASSUMED" | "UNAVAILABLE";
  source: string;
  notes: string;
  is_valid: boolean;
}

export interface ProvenanceReport {
  is_patient_specific_supported: boolean;
  readiness_summary: string;
  missing_parameters: string[];
  parameters: ProvenanceParameter[];
  unsupported_mappings: string;
  assumptions: string;
}

export interface PresetInfo {
  name: string;
  hr: number;
  contract: number;
  resist: number;
  compl: number;
  desc: string;
  category: string;
}

export interface SimMetrics {
  co: number;
  sv: number;
  sys: number;
  dia: number;
  map_val: number;
  pp: number;
  ef: number;
  hr: number;
}

export interface ComparisonRow {
  key: string;
  name: string;
  unit: string;
  description: string;
  val1: string;
  val2: string;
  diff: string;
}

export interface PresetsComparison {
  has_comparison: boolean;
  primary_preset?: string;
  compare_preset?: string;
  metrics_rows?: ComparisonRow[];
  params_rows?: [string, string, any, any][];
  disclaimer?: string;
  message?: string;
}

export interface SimulationResponse {
  success: boolean;
  scenario_label: string;
  scenario_disclaimer: string;
  sim_params: {
    hr: number;
    contract: number;
    resist: number;
    compl: number;
  };
  duration: number;
  metrics: SimMetrics;
  comparison: PresetsComparison;
}

export interface ScenarioDelta {
  field_name: string;
  display_name: string;
  unit: string;
  baseline_value: number;
  scenario_value: number;
  absolute_change: number;
  percent_change: number | null;
  has_changed: boolean;
}

export interface ScenarioMetricComparison {
  key: string;
  display_name: string;
  unit: string;
  description: string;
  baseline_value: number | null;
  scenario_value: number | null;
  absolute_difference: number | null;
  percent_difference: number | null;
  is_defined: boolean;
}

export interface ScenarioSummary {
  scenario_id: string;
  name: string;
  kind: string;
  preset: string;
  duration: number;
  created_at: string;
  associated_subject_id: number | null;
  parameters: Record<string, number>;
  disclaimer: string;
  warnings: string[];
  metrics: SimMetrics | null;
  has_error: boolean;
  execution_error: string | null;
  deltas?: ScenarioDelta[];
  metric_comparisons?: ScenarioMetricComparison[];
}

export interface ScenarioComparisonView {
  has_scenario: boolean;
  message?: string;
  current_scenario?: ScenarioSummary;
  baseline_scenario?: ScenarioSummary;
  deltas?: ScenarioDelta[];
  metric_comparisons?: ScenarioMetricComparison[];
  all_scenarios: ScenarioSummary[];
  disclaimer?: string;
  warnings?: string[];
}

export interface WhatIfResponse {
  success: boolean;
  scenario: ScenarioSummary;
  comparison: ScenarioComparisonView;
}

