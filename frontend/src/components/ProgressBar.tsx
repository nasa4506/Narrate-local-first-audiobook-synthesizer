"use client";

import { formatDuration } from "@/lib/format";
import styles from "./ProgressBar.module.css";

interface ProgressBarProps {
  completed: number;
  total: number;
  failed: number;
  elapsedSeconds?: number;
  fraction?: number; // continuous 0..1 (includes in-flight chapter progress)
}

export default function ProgressBar({
  completed,
  total,
  failed,
  elapsedSeconds,
  fraction,
}: ProgressBarProps) {
  const pct =
    fraction !== undefined
      ? Math.round(fraction * 100)
      : total > 0
        ? Math.round((completed / total) * 100)
        : 0;

  return (
    <div className={styles.wrap}>
      <div className={styles.row}>
        <span className={`mono ${styles.label}`}>
          {completed}/{total} chapters · {pct}%
          {failed > 0 ? ` · ${failed} failed` : ""}
        </span>
        {typeof elapsedSeconds === "number" && (
          <span className={`mono ${styles.label}`}>
            elapsed {formatDuration(elapsedSeconds)}
          </span>
        )}
      </div>
      <div className={styles.track}>
        <div className={styles.fill} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  );
}
