import { AnalysisResponse, HealthStatus, SampleInfo } from "@/types/cardiac";
import { HeartTabularInput, HeartTabularResponse } from "@/types/heart_tabular";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
