"use client";

import { VoiceCatalog, GPUStats, DeviceInfo } from "@/lib/api";
import GpuMeter from "./GpuMeter";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  voices: VoiceCatalog | null;
  langCode: string;
  setLangCode: (code: string) => void;
  selectedVoice: string;
  setSelectedVoice: (v: string) => void;
  speed: number;
  setSpeed: (s: number) => void;
  maxWorkers: number;
  setMaxWorkers: (n: number) => void;
  gpuStats: GPUStats | null;
  readyChapterCount: number;
  isGenerating: boolean;
  devices: DeviceInfo[] | null;
  selectedDevice: string | null;
  deviceBusy: boolean;
  onDeviceChange: (device: string) => void;
}

export default function Sidebar({
  voices,
  langCode,
  setLangCode,
  selectedVoice,
  setSelectedVoice,
  speed,
  setSpeed,
  maxWorkers,
  setMaxWorkers,
  gpuStats,
  readyChapterCount,
  isGenerating,
  devices,
  selectedDevice,
  deviceBusy,
  onDeviceChange,
}: SidebarProps) {
  if (!voices) return null;

  const langOptions = Object.entries(voices);
  const currentVoices = voices[langCode]?.voices || {};
  const voiceKeys = Object.keys(currentVoices);

  const handleLangChange = (code: string) => {
    setLangCode(code);
    const newVoices = Object.keys(voices[code]?.voices || {});
    if (newVoices.length > 0 && !newVoices.includes(selectedVoice)) {
      setSelectedVoice(newVoices[0]);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sticky}>
        <div className={styles.sectionTitle}>Narrator</div>

        {devices && devices.length > 0 && (
          <div className={styles.group}>
            <label className={styles.label} htmlFor="device-select">
              Compute device
            </label>
            <select
              id="device-select"
              className={`input ${styles.select}`}
              value={selectedDevice ?? devices[0]?.device}
              onChange={(e) => onDeviceChange(e.target.value)}
              disabled={deviceBusy || isGenerating}
            >
              {devices.map((d) => (
                <option key={d.device} value={d.device}>
                  {d.label}
                </option>
              ))}
            </select>
            {deviceBusy && (
              <div className={styles.hint}>Switching device — reloading model…</div>
            )}
          </div>
        )}

        <div className={styles.group}>
          <label className={styles.label} htmlFor="lang-select">
            Language
          </label>
          <select
            id="lang-select"
            className={`input ${styles.select}`}
            value={langCode}
            onChange={(e) => handleLangChange(e.target.value)}
          >
            {langOptions.map(([code, data]) => (
              <option key={code} value={code}>
                {data.name}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.group}>
          <label className={styles.label} htmlFor="voice-select">
            Voice
          </label>
          <select
            id="voice-select"
            className={`input ${styles.select}`}
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
          >
            {voiceKeys.map((key) => (
              <option key={key} value={key}>
                {key} — {currentVoices[key]}
              </option>
            ))}
          </select>
          {selectedVoice && currentVoices[selectedVoice] && (
            <div className={styles.voiceHint}>
              {currentVoices[selectedVoice]}
            </div>
          )}
        </div>

        <div className={styles.group}>
          <div className={styles.labelRow}>
            <label className={styles.label}>Speed</label>
            <span className={`mono ${styles.value}`}>{speed.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            className={styles.slider}
            min="0.5"
            max="2.0"
            step="0.05"
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
          />
        </div>

        <div className={styles.divider} />

        <div className={styles.group}>
          <div className={styles.labelRow}>
            <label className={styles.label}>Parallel chapters</label>
            <span className={`mono ${styles.value}`}>{maxWorkers}</span>
          </div>
          <input
            type="range"
            className={styles.slider}
            min="1"
            max="8"
            step="1"
            value={maxWorkers}
            onChange={(e) => setMaxWorkers(parseInt(e.target.value, 10))}
          />
          <div className={styles.hint}>
            Chapters are synthesized concurrently on the GPU.
          </div>
        </div>

        <GpuMeter
          stats={gpuStats}
          chapterCount={readyChapterCount}
          maxWorkers={maxWorkers}
          live={isGenerating}
        />

        <div className={styles.divider} />

        <div className={styles.foot}>
          <div className={styles.footLine}>
            <span className="mono">model</span>
            <span className="mono">Kokoro-82M</span>
          </div>
          <div className={styles.footLine}>
            <span className="mono">rate</span>
            <span className="mono">24 kHz</span>
          </div>
          <div className={styles.footLine}>
            <span className="mono">output</span>
            <span className="mono">.wav</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
