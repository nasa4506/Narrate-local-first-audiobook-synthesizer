/**
 * API client for communicating with the FastAPI TTS backend.
 */

const API_BASE = "http://localhost:8000";

/** fetch with an abort timeout so a dead/half-open backend can never hang us forever. */
async function apiFetch(url: string, init?: RequestInit, timeoutMs = 10000): Promise<Response> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(t);
  }
}

export interface VoiceCatalog {
  [langCode: string]: {
    name: string;
    voices: { [key: string]: string };
  };
}

export interface HealthInfo {
  status: string;
  model: string;
  cuda_available: boolean;
  gpu_name: string | null;
  sample_rate: number;
  total_voices: number;
}

export interface GPUStats {
  cuda_available: boolean;
  gpu_name: string | null;
  total_bytes: number | null;
  free_bytes: number | null;
  allocated_bytes: number | null;
  reserved_bytes: number | null;
  base_bytes: number | null;
}

export interface ChapterInput {
  title: string;
  text: string;
}

export type ChapterState = "queued" | "generating" | "done" | "error";

export interface ChapterStatus {
  title: string;
  status: ChapterState;
  error?: string | null;
  elapsed?: number | null;
  est_audio_sec?: number | null;
  progress?: number | null;
  audio_sec_done?: number | null;
  gen_time?: number | null;
  duration?: number | null;
  rtf?: number | null;
  phonemes?: string | null;
  audio_base64?: string | null;
}

export interface AudiobookStatus {
  job_id: string;
  status: "running" | "done" | "failed";
  total: number;
  completed: number;
  failed: number;
  chapters: ChapterStatus[];
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await apiFetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = d?.loc?.filter((l: unknown) => l !== "body").join(".");
        const msg = d?.msg || "";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join("; ");
  }
  return fallback;
}

export async function fetchVoices(): Promise<VoiceCatalog> {
  const res = await apiFetch(`${API_BASE}/api/voices`);
  if (!res.ok) throw new Error("Failed to fetch voices");
  return res.json();
}

export async function fetchGpuStats(): Promise<GPUStats> {
  const res = await apiFetch(`${API_BASE}/api/gpu`);
  if (!res.ok) throw new Error("Failed to fetch GPU stats");
  return res.json();
}

export async function startAudiobook(
  chapters: ChapterInput[],
  voice: string,
  langCode: string,
  speed: number,
  maxWorkers: number
): Promise<{ job_id: string; total: number }> {
  const res = await apiFetch(`${API_BASE}/api/audiobook/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chapters,
      voice,
      lang_code: langCode,
      speed,
      max_workers: maxWorkers,
    }),
  }, 30000);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Generation failed" }));
    throw new Error(errorMessage(err.detail, "Generation failed"));
  }

  return res.json();
}

export class JobNotFoundError extends Error {
  constructor(jobId: string) {
    super(`Job ${jobId} no longer exists`);
    this.name = "JobNotFoundError";
  }
}

export async function fetchAudiobookStatus(
  jobId: string
): Promise<AudiobookStatus> {
  const res = await apiFetch(`${API_BASE}/api/audiobook/status/${jobId}`);
  if (res.status === 404) throw new JobNotFoundError(jobId);
  if (!res.ok) throw new Error("Failed to fetch job status");
  return res.json();
}

export interface SingleSynthResult {
  audioBlob: Blob;
  audioUrl: string;
  genTime: number;
  duration: number;
}

export async function synthesize(
  text: string,
  voice: string,
  langCode: string,
  speed: number
): Promise<SingleSynthResult> {
  const res = await apiFetch(
    `${API_BASE}/api/synthesize`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, lang_code: langCode, speed }),
    },
    900000
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Synthesis failed" }));
    throw new Error(errorMessage(err.detail, "Synthesis failed"));
  }

  const blob = await res.blob();
  return {
    audioBlob: blob,
    audioUrl: URL.createObjectURL(blob),
    genTime: parseFloat(res.headers.get("X-Gen-Time") || "0"),
    duration: parseFloat(res.headers.get("X-Duration") || "0"),
  };
}

export function audiobookZipUrl(jobId: string): string {
  return `${API_BASE}/api/audiobook/download/${jobId}`;
}

export function base64ToBlob(base64: string, type = "audio/wav"): Blob {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type });
}

export function base64ToAudioUrl(base64: string): string {
  return URL.createObjectURL(base64ToBlob(base64));
}

export function sanitizeFilename(name: string, fallback: string): string {
  const clean = name
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/\s+/g, " ")
    .trim();
  const base = clean || fallback;
  return base.toLowerCase().endsWith(".wav") ? base : `${base}.wav`;
}
