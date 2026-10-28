import { AnalysisResponse, HealthStatus, SampleInfo } from "@/types/cardiac";

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
