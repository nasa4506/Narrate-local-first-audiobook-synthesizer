"use client";

import { GPUStats } from "@/lib/api";
import styles from "./GpuMeter.module.css";

const BASE_FALLBACK = 1.1 * 1024 ** 3; // model + CUDA context (before measurement)
const WORKING_PER_CHAPTER = 320 * 1024 ** 2; // est. activation peak per concurrent pass

function fmtGB(bytes: number): string {
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

interface GpuMeterProps {
  stats: GPUStats | null;
  chapterCount: number; // chapters with text
  maxWorkers: number;
  live: boolean; // true while a job is generating → show real usage
}

export default function GpuMeter({
  stats,
  chapterCount,
  maxWorkers,
  live,
}: GpuMeterProps) {
  if (!stats) {
    return (
      <div className={styles.wrap}>
        <div className={styles.labelRow}>
          <span className={styles.label}>GPU memory</span>
          <span className={`mono ${styles.value}`}>—</span>
        </div>
      </div>
    );
  }

  if (!stats.cuda_available) {
    return (
      <div className={styles.wrap}>
        <div className={styles.labelRow}>
          <span className={styles.label}>GPU memory</span>
          <span className={`mono ${styles.value}`}>CPU mode</span>
        </div>
      </div>
    );
  }

  const total = stats.total_bytes ?? 0;
  const base = stats.base_bytes ?? BASE_FALLBACK;
  const concurrent = Math.min(maxWorkers, chapterCount);
  const estPeak = base + concurrent * WORKING_PER_CHAPTER;

  const usedBytes = live
    ? stats.allocated_bytes ?? estPeak
    : Math.max(base, estPeak);
  const pct = total > 0 ? usedBytes / total : 0;
  const level =
    pct >= 0.9 ? styles.red : pct >= 0.75 ? styles.amber : styles.ok;

  const sub = live
    ? `allocated ${fmtGB(stats.allocated_bytes ?? 0)} · reserved ${fmtGB(stats.reserved_bytes ?? 0)}`
    : concurrent > 0
      ? `est. peak · base + ${concurrent}× work`
      : "est. peak · base only";

  return (
    <div className={styles.wrap}>
      <div className={styles.labelRow}>
        <span className={styles.label}>
          GPU memory {live ? "· live" : "· estimate"}
        </span>
        <span className={`mono ${styles.value}`}>
          {fmtGB(usedBytes)} / {fmtGB(total)} ({Math.round(pct * 100)}%)
        </span>
      </div>
      <div className={`${styles.track} ${level}`}>
        <div
          className={styles.fill}
          style={{ width: `${Math.min(100, pct * 100)}%` }}
        />
      </div>
      <div className={styles.sub}>{sub}</div>
    </div>
  );
}
