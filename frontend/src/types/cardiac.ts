export type CardiacClass = "NOR" | "DCM" | "HCM" | "MINF" | "RV" | "UNKNOWN";

export interface Biomarker {
  key: string;
  description: string;
  value: number | null;
  unit: string;
  category: "LV Function" | "RV Function" | "Myocardium" | "BSA-Indexed" | "Geometry & Ratios" | "Wall Thickness" | "General";
  normal_range?: string;
}

export interface DiagnosisInfo {
  predicted_class?: CardiacClass | null;
  predicted_full_name?: string | null;
  /** Confidence as a percentage, only when a classifier produced a valid result. */
  confidence?: number | null;
  /** Per-class probabilities as fractions in [0, 1]. */
  probabilities?: Partial<Record<CardiacClass, number | null>> | null;
  headline?: string | null;
  details?: string | null;
  description?: string | null;
  /** Legacy response fields retained during API transition. */
  prediction?: string;
  prediction_full_name?: string;
  confidence_percent?: number | null;
  class_probabilities?: Record<string, number> | null;
}

export interface SliceData {
  slice_index: number;
  ed_overlay: string; // base64 PNG data URL
  es_overlay: string; // base64 PNG data URL
  ed_raw: string;     // base64 PNG data URL
  es_raw: string;     // base64 PNG data URL
}

export interface AnalysisMetadata {
  num_slices: number;
  mid_slice: number;
  dimensions: [number, number, number];
  voxel_spacing: [number, number, number];
  patient_bsa: number;
  height_cm: number;
  weight_kg: number;
  tta_enabled: boolean;
  patient_id?: string;
  patient_id_verified?: boolean;
  verification_status?: "metadata-verified" | "user-confirmed" | "unverified";
  warnings?: string[];
}

export interface AnalysisResponse {
  success: boolean;
  metadata: AnalysisMetadata;
  diagnosis: DiagnosisInfo;
  biomarkers: Biomarker[];
  slices: SliceData[];
}

export interface HealthStatus {
  status: string;
  service: string;
  device: string;
  img_size: number;
  ensemble_folds: number[];
  models_ready: boolean;
  supported_formats: string[];
}

export interface SampleInfo {
  available: boolean;
  patient_id: string;
  ground_truth_class: string;
  default_height_cm: number;
  default_weight_kg: number;
  ed_frame: number;
  es_frame: number;
  description: string;
}
