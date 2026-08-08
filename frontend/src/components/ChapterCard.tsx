"use client";

import { useState } from "react";
import { sanitizeFilename } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import styles from "./ChapterCard.module.css";

export type ChapterState =
  | "idle"
  | "queued"
  | "generating"
  | "done"
  | "error";

export interface ChapterItem {
  id: string;
  title: string;
  text: string;
  fileName: string;
  state: ChapterState;
  error?: string;
  genTime?: number;
  duration?: number;
  audioUrl?: string;
  generatedAt?: number;
  estAudioSec?: number;
  progress?: number; // 0..1 while generating (audio produced vs estimate)
  audioSecDone?: number;
}

interface ChapterCardProps {
  chapter: ChapterItem;
  index: number;
  canDelete: boolean;
  now: number;
  onUpdate: (patch: Partial<ChapterItem>) => void;
  onDelete: () => void;
  onRetry: () => void;
}

const STATUS_LABEL: Record<ChapterState, string> = {
  idle: "idle",
  queued: "queued",
  generating: "synthesizing",
  done: "ready",
  error: "error",
};

export default function ChapterCard({
  chapter,
  index,
  canDelete,
  now,
  onUpdate,
  onDelete,
  onRetry,
}: ChapterCardProps) {
  const [expanded, setExpanded] = useState(true);
  const busy = chapter.state === "queued" || chapter.state === "generating";

  const elapsedSec =
    chapter.state === "generating" && chapter.generatedAt
      ? Math.max(0, (now - chapter.generatedAt) / 1000)
      : 0;

  const handleDownload = () => {
    if (!chapter.audioUrl) return;
    const a = document.createElement("a");
    a.href = chapter.audioUrl;
    a.download = sanitizeFilename(chapter.fileName, `chapter_${index + 1}`);
    a.click();
  };

  return (
    <div
      className={`${styles.card} ${
        chapter.state === "error" ? styles.cardError : ""
      }`}
    >
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.index}>{String(index + 1).padStart(2, "0")}</span>
        <input
          className={styles.titleInput}
          value={chapter.title}
          onChange={(e) => onUpdate({ title: e.target.value })}
          placeholder="Chapter title…"
          disabled={busy}
        />
        <span
          className={`${styles.status} ${styles[`status${chapter.state}`]}`}
        >
          {busy && <span className="spinner" />}
          {STATUS_LABEL[chapter.state]}
        </span>
        <button
          className={styles.iconBtn}
          title={expanded ? "Collapse" : "Expand"}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "−" : "+"}
        </button>
        {canDelete && (
          <button
            className={`${styles.iconBtn} ${styles.deleteBtn}`}
            title="Remove chapter"
            onClick={onDelete}
            disabled={busy}
          >
            ×
          </button>
        )}
      </div>

      {/* Body */}
      {expanded && (
        <div className={styles.body}>
          <textarea
            className={styles.textarea}
            value={chapter.text}
            onChange={(e) => onUpdate({ text: e.target.value })}
            placeholder="Paste the chapter text here…"
            disabled={busy}
          />

          {chapter.state === "generating" && (
            <div className={styles.genRow}>
              {typeof chapter.progress === "number" ? (
                <div className={styles.detBar}>
                  <div
                    className={styles.detFill}
                    style={{ width: `${Math.min(100, chapter.progress * 100)}%` }}
                  />
                </div>
              ) : (
                <div className="shimmerBar" />
              )}
              <span className={`mono ${styles.genHint}`}>
                synthesizing on GPU ·{" "}
                {typeof chapter.progress === "number"
                  ? `${Math.round(chapter.progress * 100)}% · `
                  : ""}
                {formatDuration(elapsedSec)} elapsed
                {chapter.estAudioSec
                  ? ` · est. ${formatDuration(chapter.estAudioSec)} audio`
                  : ""}
              </span>
            </div>
          )}

          {chapter.state === "error" && chapter.error && (
            <div className={styles.errorBox}>
              <span>{chapter.error}</span>
              <button className="btn" onClick={onRetry}>
                Retry
              </button>
            </div>
          )}

          {chapter.state === "done" && chapter.audioUrl && (
            <div className={styles.result}>
              <div className={styles.playerRow}>
                <audio controls src={chapter.audioUrl} />
                <button className="btn" onClick={handleDownload}>
                  Download .wav
                </button>
              </div>
              <div className={`mono ${styles.meta}`}>
                <span>{chapter.duration?.toFixed(2)}s audio</span>
                <span>{chapter.genTime?.toFixed(2)}s gen</span>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className={styles.footer}>
            <div className={styles.fileNameWrap}>
              <span className={styles.fileLabel}>File name</span>
              <input
                className={`input ${styles.fileInput}`}
                value={chapter.fileName}
                onChange={(e) => onUpdate({ fileName: e.target.value })}
                placeholder={`chapter_${index + 1}`}
                disabled={busy}
              />
              <span className={`mono ${styles.ext}`}>.wav</span>
            </div>
            <span className={`mono ${styles.charCount}`}>
              {chapter.text.length.toLocaleString()} chars
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
