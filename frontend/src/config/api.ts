import { AnalysisResponse, HealthStatus, SampleInfo } from "@/types/cardiac";
import { HeartTabularInput, HeartTabularResponse } from "@/types/heart_tabular";
import {
  CategoryAnalysis,
  ObservationsResponse,
  PatientListResponse,
  PatientSummary,
  PresetInfo,
  ProvenanceReport,
  ScenarioComparisonView,
  SimulationResponse,
  TrendCategory,
  WhatIfResponse,
} from "@/types/cardiovascular_twin";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// =============================================================================
// Common & System Health
// =============================================================================

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API health check failed with HTTP ${res.status}`);
  }
  return res.json();
}

// =============================================================================
// Module I: Cardiac MRI Analysis
// =============================================================================

export async function fetchSampleInfo(): Promise<SampleInfo> {
  const res = await fetch(`${API_BASE_URL}/api/sample-info`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load sample info (HTTP ${res.status})`);
  }
  return res.json();
}

export async function submitAnalysis(formData: FormData): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = `Analysis failed with HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

// =============================================================================
// Module II: Heart Disease Tabular Risk Prediction
// =============================================================================

export async function predictHeartTabular(
  patientData: HeartTabularInput
): Promise<HeartTabularResponse> {
  const res = await fetch(`${API_BASE_URL}/api/heart-tabular/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(patientData),
  });

  if (!res.ok) {
    let errorDetail = `Prediction failed with HTTP ${res.status}`;
    try {
      const errJson = await res.json();
      if (typeof errJson.detail === "string") {
        errorDetail = errJson.detail;
      } else if (Array.isArray(errJson.detail)) {
        errorDetail = errJson.detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function fetchHeartTabularSample(): Promise<HeartTabularInput> {
  const res = await fetch(`${API_BASE_URL}/api/heart-tabular/sample`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load sample patient (HTTP ${res.status})`);
  }
  return res.json();
}

// =============================================================================
// Module III: Cardiovascular Digital Twin & CardioSim Simulation Engine
// =============================================================================

export async function fetchPatients(
  search?: string,
  limit: number = 50,
  offset: number = 0
): Promise<PatientListResponse> {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/patients?${params.toString()}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load patient cohort (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPatientProfile(subjectId: number): Promise<{ success: boolean; summary: PatientSummary }> {
  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/patients/${subjectId}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load patient ${subjectId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPatientObservations(
  subjectId: number,
  category?: string,
  measurementName?: string,
  limit: number = 100,
  offset: number = 0
): Promise<ObservationsResponse> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (measurementName) params.set("measurement_name", measurementName);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const res = await fetch(
    `${API_BASE_URL}/api/cardio-twin/patients/${subjectId}/observations?${params.toString()}`,
    {
      cache: "no-store",
      headers: { Accept: "application/json" },
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to load observations for patient ${subjectId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPatientTrends(
  subjectId: number
): Promise<{ subject_id: number; trends: TrendCategory[] }> {
  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/patients/${subjectId}/trends`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load trends for patient ${subjectId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPatientAnalysis(
  subjectId: number
): Promise<{ subject_id: number; analysis: CategoryAnalysis[] }> {
  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/patients/${subjectId}/analysis`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load cardiovascular analysis for patient ${subjectId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchPatientProvenance(
  subjectId: number
): Promise<{ subject_id: number; provenance: ProvenanceReport; parameter_bounds: Record<string, any> }> {
  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/patients/${subjectId}/provenance`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to evaluate provenance for patient ${subjectId} (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchCardioPresets(): Promise<{
  success: boolean;
  presets: Record<string, PresetInfo>;
  parameter_bounds: Record<string, any>;
}> {
  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/presets`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to load CardioSim presets (HTTP ${res.status})`);
  }
  return res.json();
}

export async function runPresetSimulation(
  payload: {
    subject_id: number;
    preset_name: string;
    duration?: number;
    compare_preset?: string;
    session_id?: string;
  },
  sessionId?: string
): Promise<SimulationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (sessionId) headers["x-session-id"] = sessionId;

  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/simulate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorDetail = `Simulation failed with HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function runWhatIfScenario(
  payload: {
    subject_id?: number;
    scenario_name: string;
    preset_name: string;
    hr: number;
    contract: number;
    resist: number;
    compl: number;
    duration?: number;
    session_id?: string;
  },
  sessionId?: string
): Promise<WhatIfResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (sessionId) headers["x-session-id"] = sessionId;

  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/scenarios/run`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorDetail = `Scenario run failed with HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export async function fetchScenarios(sessionId?: string): Promise<{
  session_id: string;
  scenarios: any[];
  comparison: ScenarioComparisonView;
}> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (sessionId) headers["x-session-id"] = sessionId;

  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/scenarios`, {
    cache: "no-store",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to load scenarios (HTTP ${res.status})`);
  }
  return res.json();
}

export async function clearScenarios(sessionId?: string): Promise<{ success: boolean; message: string }> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (sessionId) headers["x-session-id"] = sessionId;

  const res = await fetch(`${API_BASE_URL}/api/cardio-twin/scenarios`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to clear scenarios (HTTP ${res.status})`);
  }
  return res.json();
}
