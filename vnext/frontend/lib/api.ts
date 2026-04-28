import type {
  APIResponse,
  AnalysisDetail,
  EvidenceDetail,
  Municipality,
  Neighborhood,
  SpeechDetail,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });

  let payload: APIResponse<T> | null = null;
  try {
    payload = (await response.json()) as APIResponse<T>;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      payload?.error ||
      payload?.message ||
      (typeof payload?.data === "string" ? payload.data : null) ||
      `HTTP ${response.status}`;
    throw new Error(message);
  }

  if (!payload) {
    throw new Error("Respuesta vacía del servidor");
  }

  return payload.data;
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body?.detail || body?.message || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return await response.blob();
}

export const territory = {
  municipalities: () => request<Municipality[]>("/territory/municipalities"),
  neighborhoods: (municipalityId: string) =>
    request<Neighborhood[]>(`/territory/neighborhoods/${municipalityId}`),
};

export const evidence = {
  latest: (municipalityId: string) =>
    request<EvidenceDetail>(`/evidence/latest/${municipalityId}`),
};

export const analysis = {
  run: (payload: {
    municipality_id: string;
    objective?: string;
    force_refresh?: boolean;
  }) =>
    request<AnalysisDetail>("/analysis/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  latest: (municipalityId: string) =>
    request<AnalysisDetail>(`/analysis/latest/${municipalityId}`),
};

export const speech = {
  run: (payload: {
    municipality_id: string;
    speech_goal: string;
    audience: string;
    tone: string;
    channel: string;
    duration_minutes: number;
    force_refresh?: boolean;
    source_text?: string;
    priority_topics?: string[];
    avoid_topics?: string[];
    electoral_moment?: string;
    neighborhood_id?: string;
  }) =>
    request<SpeechDetail>("/speech/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  latest: (municipalityId: string) =>
    request<SpeechDetail>(`/speech/latest/${municipalityId}`),
};

export const exports = {
  speechBlob: (speechId: string) =>
    requestBlob(`/exports/pdf/speech/${speechId}`),
  analysisBlob: (analysisId: string) =>
    requestBlob(`/exports/pdf/analysis/${analysisId}`),
};

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}