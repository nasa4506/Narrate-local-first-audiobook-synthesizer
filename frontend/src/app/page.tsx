"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import ChaptersPanel from "@/components/ChaptersPanel";
import { ChapterItem } from "@/components/ChapterCard";
import {
  fetchHealth,
  fetchVoices,
  fetchGpuStats,
  fetchDevices,
  setDevice,
  startAudiobook,
  fetchAudiobookStatus,
  synthesize,
  audiobookZipUrl,
  base64ToBlob,
  JobNotFoundError,
  HealthInfo,
  VoiceCatalog,
  GPUStats,
  DeviceInfo,
  ChapterState,
} from "@/lib/api";
import styles from "./page.module.css";

// ------------------------------------------------------------------
// Refresh persistence (localStorage) — module-scope so it loads once
// ------------------------------------------------------------------

const STORAGE_KEY = "narrate.state.v1";

let chapterCounter = 0;

interface PersistedState {
  chapters: ChapterItem[];
  langCode: string;
  voice: string;
  speed: number;
  maxWorkers: number;
  device: string | null;
  zipJobId: string | null;
  activeJobId: string | null;
  chapterCounter: number;
}

function defaultState(): PersistedState {
  return {
    chapters: [],
    langCode: "a",
    voice: "af_heart",
    speed: 1.0,
    maxWorkers: 4,
    device: null,
    zipJobId: null,
    activeJobId: null,
    chapterCounter: 0,
  };
}

function loadPersisted(): PersistedState {
  if (typeof window === "undefined") return defaultState();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw) as Partial<PersistedState>;
    const merged: PersistedState = { ...defaultState(), ...parsed };

    merged.chapters = (Array.isArray(parsed.chapters) ? parsed.chapters : []).map(
      (c) => ({
        id: typeof c.id === "string" ? c.id : crypto.randomUUID(),
        title: typeof c.title === "string" ? c.title : "",
        text: typeof c.text === "string" ? c.text : "",
        fileName: typeof c.fileName === "string" ? c.fileName : "Chapter",
        state: "idle" as ChapterState,
      })
    );

    // Audio blobs/URLs do not survive a refresh; keep a working zip link only.
    chapterCounter = Math.max(merged.chapterCounter, merged.chapters.length);
    return merged;
  } catch {
    return defaultState();
  }
}

function createChapter(): ChapterItem {
  chapterCounter += 1;
  return {
    id: crypto.randomUUID(),
    title: "",
    text: "",
    fileName: `Chapter ${chapterCounter}`,
    state: "idle",
  };
}

export default function Home() {
  // ----- Data -----
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [voices, setVoices] = useState<VoiceCatalog | null>(null);
  const [gpuStats, setGpuStats] = useState<GPUStats | null>(null);
  const [connectionError, setConnectionError] = useState(false);

  // ----- Compute device -----
  const [devices, setDevices] = useState<DeviceInfo[] | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [deviceBusy, setDeviceBusy] = useState(false);
  const pendingDeviceRef = useRef<string | null>(null);

  // ----- Narrator settings -----
  const [langCode, setLangCode] = useState("a");
  const [selectedVoice, setSelectedVoice] = useState("af_heart");
  const [speed, setSpeed] = useState(1.0);
  const [maxWorkers, setMaxWorkers] = useState(4);

  // ----- Manuscript -----
  const [chapters, setChapters] = useState<ChapterItem[]>([]);
  const chaptersRef = useRef<ChapterItem[]>([]);
  useEffect(() => {
    chaptersRef.current = chapters;
  }, [chapters]);

  // ----- Job state -----
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeJobRef = useRef<string | null>(null);
  const [zipJobId, setZipJobId] = useState<string | null>(null);

  // ----- Live clocks (elapsed timers while generating) -----
  const [now, setNow] = useState<number>(0);
  const [jobStartedAt, setJobStartedAt] = useState<number | null>(null);

  useEffect(() => {
    if (!isGenerating) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [isGenerating]);

  // ----- Persist state (debounced) -----
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        window.localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            chapters,
            langCode,
            voice: selectedVoice,
            speed,
            maxWorkers,
            device: selectedDevice,
            zipJobId,
            activeJobId: activeJobRef.current,
            chapterCounter,
          } satisfies PersistedState)
        );
      } catch {
        // storage full/unavailable — non-fatal
      }
    }, 400);
    return () => clearTimeout(t);
  }, [chapters, langCode, selectedVoice, speed, maxWorkers, zipJobId, isGenerating, selectedDevice]);

  // ----- Initial data load -----
  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchHealth(), fetchVoices(), fetchDevices()])
      .then(([h, v, d]) => {
        if (!cancelled) {
          setHealth(h);
          setVoices(v);
          setDevices(d.devices);
          setSelectedDevice((prev) => prev ?? d.current);
          setConnectionError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setConnectionError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ----- Switch compute device (GPU ↔ CPU) -----
  const handleDeviceChange = async (device: string) => {
    if (deviceBusy || isGenerating || device === selectedDevice) return;
    setDeviceBusy(true);
    setError(null);
    try {
      await setDevice(device);
      setSelectedDevice(device);
      const h = await fetchHealth();
      setHealth(h);
      fetchGpuStats()
        .then((s) => setGpuStats(s))
        .catch(() => {});
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Device switch failed (is a job generating?)"
      );
    } finally {
      setDeviceBusy(false);
    }
  };

  // ----- Apply a persisted device once the device list is known -----
  useEffect(() => {
    const pending = pendingDeviceRef.current;
    if (!pending || !devices || !health) return;
    const available = devices.some((d) => d.device === pending);
    if (!available) {
      pendingDeviceRef.current = null;
      return;
    }
    if (pending === health.device) {
      pendingDeviceRef.current = null;
      setSelectedDevice(pending);
      return;
    }
    pendingDeviceRef.current = null;
    handleDeviceChange(pending);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devices, health]);

  // ----- Auto-reconnect: retry the backend while unreachable -----
  const [retryTick, setRetryTick] = useState(0);
  useEffect(() => {
    if (!connectionError) return;
    let cancelled = false;
    let t: ReturnType<typeof setTimeout>;
    const attempt = async () => {
      if (cancelled) return;
      try {
        const [h, v] = await Promise.all([fetchHealth(), fetchVoices()]);
        if (!cancelled) {
          setHealth(h);
          setVoices(v);
          setConnectionError(false);
          fetchGpuStats()
            .then((s) => {
              if (!cancelled) setGpuStats(s);
            })
            .catch(() => {});
        }
      } catch {
        if (!cancelled) t = setTimeout(attempt, 5000);
      }
    };
    attempt();
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [connectionError, retryTick]);

  // ----- Restore persisted state after hydration (SSR-safe) -----
  const restoredRef = useRef(false);
  useEffect(() => {
    const t = setTimeout(() => {
      if (restoredRef.current) return;
      restoredRef.current = true;

      const persisted = loadPersisted();
      chapterCounter = persisted.chapterCounter;
      setChapters(persisted.chapters);
      setLangCode(persisted.langCode);
      setSelectedVoice(persisted.voice);
      setSpeed(persisted.speed);
      setMaxWorkers(persisted.maxWorkers);
      setZipJobId(persisted.zipJobId);

      if (persisted.device) pendingDeviceRef.current = persisted.device;

      if (persisted.activeJobId) {
        activeJobRef.current = persisted.activeJobId;
        setIsGenerating(true);
      }
    }, 0);
    return () => clearTimeout(t);
  }, []);

  // ----- GPU memory polling: once + every 2s while generating -----
  useEffect(() => {
    let cancelled = false;
    const refresh = () =>
      fetchGpuStats()
        .then((s) => {
          if (!cancelled) setGpuStats(s);
        })
        .catch(() => {});
    refresh();
    if (!isGenerating) {
      return () => {
        cancelled = true;
      };
    }
    const t = setInterval(refresh, 2000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [isGenerating, chapters.length, maxWorkers]);

  // ----- Manuscript actions -----
  const addChapter = () => setChapters((prev) => [...prev, createChapter()]);

  const updateChapter = (id: string, patch: Partial<ChapterItem>) =>
    setChapters((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const deleteChapter = (id: string) =>
    setChapters((prev) => prev.filter((c) => c.id !== id));

  // ----- Poll job progress -----
  const pollStatus = useCallback(async (job: string) => {
    const status = await fetchAudiobookStatus(job);

    const current = chaptersRef.current;
    const readyIndices = current
      .map((c, i) => (c.text.trim().length > 0 ? i : -1))
      .filter((i) => i >= 0);

    const next = current.map((ch, i) => {
      const statusIdx = readyIndices.indexOf(i);
      if (statusIdx === -1) return ch;
      const meta = status.chapters[statusIdx];
      if (!meta) return ch;

      if (meta.status === "done" && meta.audio_base64 && ch.state !== "done") {
        return {
          ...ch,
          state: "done" as ChapterState,
          error: undefined,
          genTime: meta.gen_time ?? undefined,
          duration: meta.duration ?? undefined,
          audioUrl: URL.createObjectURL(base64ToBlob(meta.audio_base64)),
        };
      }
      if (meta.status === "error") {
        return {
          ...ch,
          state: "error" as ChapterState,
          error: meta.error || "Generation failed",
          audioUrl: undefined,
        };
      }
      if (meta.status === "queued") {
        return {
          ...ch,
          state: "queued" as ChapterState,
          generatedAt: undefined,
          estAudioSec: ch.estAudioSec ?? meta.est_audio_sec ?? undefined,
          progress: 0,
          audioSecDone: 0,
        };
      }
      if (meta.status === "generating") {
        return {
          ...ch,
          state: "generating" as ChapterState,
          generatedAt: ch.generatedAt ?? Date.now(),
          estAudioSec: ch.estAudioSec ?? meta.est_audio_sec ?? undefined,
          progress: meta.progress ?? 0,
          audioSecDone: meta.audio_sec_done ?? 0,
        };
      }
      return ch;
    });

    if (status.status !== "running") {
      setZipJobId(job);
      activeJobRef.current = null;
      setChapters(
        next.map((ch) =>
          ch.text.trim().length > 0 &&
          ch.state !== "done" &&
          ch.state !== "error"
            ? { ...ch, state: "error" as ChapterState, error: "No result" }
            : ch
        )
      );
      setIsGenerating(false);
    } else {
      setChapters(next);
    }
  }, []);

  // ----- Generate all (parallel) -----
  const handleGenerateAll = async () => {
    if (isGenerating) return;
    setError(null);

    const ready = chaptersRef.current.filter((c) => c.text.trim().length > 0);
    if (ready.length === 0) {
      setError("Add some chapter text before generating.");
      return;
    }

    chaptersRef.current.forEach((c) => {
      if (c.audioUrl) URL.revokeObjectURL(c.audioUrl);
    });

    setChapters((prev) =>
      prev.map((c) => ({
        ...c,
        state: "queued" as ChapterState,
        error: undefined,
        genTime: undefined,
        duration: undefined,
        audioUrl: undefined,
        generatedAt: undefined,
        estAudioSec: undefined,
        progress: 0,
        audioSecDone: 0,
      }))
    );

    setJobStartedAt(Date.now());
    setIsGenerating(true);

    try {
      const { job_id } = await startAudiobook(
        ready.map((c) => ({ title: c.title, text: c.text })),
        selectedVoice,
        langCode,
        speed,
        maxWorkers
      );
      activeJobRef.current = job_id;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
      setJobStartedAt(null);
      setChapters((prev) =>
        prev.map((c) =>
          c.state === "queued"
            ? { ...c, state: "idle" as ChapterState, generatedAt: undefined }
            : c
        )
      );
      setIsGenerating(false);
    }
  };

  // ----- Polling loop -----
  const pollingRef = useRef(false);
  useEffect(() => {
    if (!isGenerating) return;
    const interval = setInterval(() => {
      const job = activeJobRef.current;
      if (!job || pollingRef.current) return;
      pollingRef.current = true;
      pollStatus(job)
        .catch((err) => {
          activeJobRef.current = null;
          if (err instanceof JobNotFoundError) {
            // Job died with the backend (e.g. it was restarted) — recover cleanly.
            setJobStartedAt(null);
            setZipJobId(null);
            setChapters((prev) =>
              prev.map((c) =>
                c.state === "queued" || c.state === "generating"
                  ? {
                      ...c,
                      state: "idle" as ChapterState,
                      progress: undefined,
                      generatedAt: undefined,
                      audioSecDone: undefined,
                    }
                  : c
              )
            );
            setError(
              "The previous generation job is no longer available (was the backend restarted?). Your chapters are safe — press Generate all to start again."
            );
          } else {
            // Network/backend failure — flag it so the auto-reconnect kicks in.
            setConnectionError(true);
            setError(
              err && err.name === "AbortError"
                ? "Backend not responding — auto-reconnecting…"
                : err instanceof Error
                  ? `Cannot reach backend: ${err.message}`
                  : "Cannot reach backend"
            );
          }
          setIsGenerating(false);
        })
        .finally(() => {
          pollingRef.current = false;
        });
    }, 600);
    return () => clearInterval(interval);
  }, [isGenerating, pollStatus]);

  // ----- Retry a single failed chapter -----
  const retryChapter = async (id: string) => {
    const ch = chaptersRef.current.find((c) => c.id === id);
    if (!ch || ch.text.trim().length === 0 || isGenerating) return;
    setError(null);
    updateChapter(id, { state: "generating", error: undefined });

    try {
      const result = await synthesize(ch.text, selectedVoice, langCode, speed);
      updateChapter(id, {
        state: "done",
        genTime: result.genTime,
        duration: result.duration,
        audioUrl: result.audioUrl,
      });
    } catch (err) {
      updateChapter(id, {
        state: "error",
        error: err instanceof Error ? err.message : "Retry failed",
      });
    }
  };

  const hasResults =
    chapters.some((c) => c.state === "done") || zipJobId !== null;
  const readyChapterCount = chapters.filter(
    (c) => c.text.trim().length > 0
  ).length;

  return (
    <div className={styles.appLayout}>
      <Sidebar
        voices={voices}
        langCode={langCode}
        setLangCode={setLangCode}
        selectedVoice={selectedVoice}
        setSelectedVoice={setSelectedVoice}
        speed={speed}
        setSpeed={setSpeed}
        maxWorkers={maxWorkers}
        setMaxWorkers={setMaxWorkers}
        gpuStats={gpuStats}
        readyChapterCount={readyChapterCount}
        isGenerating={isGenerating}
        devices={devices}
        selectedDevice={selectedDevice}
        deviceBusy={deviceBusy}
        onDeviceChange={handleDeviceChange}
      />

      <main className={styles.mainContent}>
        <Header health={health} />

        {connectionError && (
          <div className={styles.connectionError}>
            <span>
              Cannot reach the TTS backend at localhost:8000 — retrying
              automatically. Start it with: uvicorn main:app
            </span>
            <button
              className={styles.retryBtn}
              onClick={() => setRetryTick((t) => t + 1)}
            >
              Retry now
            </button>
          </div>
        )}

        <div className={styles.workspace}>
          {error && (
            <div
              style={{
                marginBottom: 16,
                padding: "10px 16px",
                borderRadius: "var(--radius-md)",
                background: "rgba(248, 113, 113, 0.07)",
                border: "1px solid rgba(248, 113, 113, 0.25)",
                color: "var(--danger)",
                fontSize: "0.82rem",
              }}
            >
              ⚠ {error}
            </div>
          )}

          <ChaptersPanel
            chapters={chapters}
            isGenerating={isGenerating}
            now={now}
            jobStartedAt={jobStartedAt}
            onAdd={addChapter}
            onUpdate={updateChapter}
            onDelete={deleteChapter}
            onRetry={retryChapter}
            onGenerateAll={handleGenerateAll}
            onDownloadZip={() => {
              if (zipJobId) {
                const a = document.createElement("a");
                a.href = audiobookZipUrl(zipJobId);
                a.download = `audiobook_${zipJobId}.zip`;
                a.click();
              }
            }}
            hasResults={hasResults}
            generatingAll={isGenerating}
          />

          <p className={`mono ${styles.footNote}`}>
            Narrate runs 100% locally — no cloud, no uploads. Chapters
            auto-save to this browser.
          </p>
        </div>
      </main>
    </div>
  );
}
