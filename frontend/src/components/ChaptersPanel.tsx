"use client";

import ChapterCard, { ChapterItem } from "./ChapterCard";
import ProgressBar from "./ProgressBar";
import styles from "./ChaptersPanel.module.css";

interface ChaptersPanelProps {
  chapters: ChapterItem[];
  isGenerating: boolean;
  now: number;
  jobStartedAt: number | null;
  onAdd: () => void;
  onUpdate: (id: string, patch: Partial<ChapterItem>) => void;
  onDelete: (id: string) => void;
  onRetry: (id: string) => void;
  onGenerateAll: () => void;
  onDownloadZip: () => void;
  hasResults: boolean;
  generatingAll: boolean;
}

export default function ChaptersPanel({
  chapters,
  isGenerating,
  now,
  jobStartedAt,
  onAdd,
  onUpdate,
  onDelete,
  onRetry,
  onGenerateAll,
  onDownloadZip,
  hasResults,
  generatingAll,
}: ChaptersPanelProps) {
  const ready = chapters.filter((c) => c.text.trim().length > 0).length;
  const completed = chapters.filter((c) => c.state === "done").length;
  const failed = chapters.filter((c) => c.state === "error").length;

  // Continuous job-level progress: done=1, generating=their in-flight fraction
  const fraction =
    ready > 0
      ? chapters.reduce((acc, c) => {
          if (c.state === "done") return acc + 1;
          if (c.state === "generating") return acc + Math.min(1, c.progress ?? 0);
          return acc;
        }, 0) / ready
      : 0;

  return (
    <section className={styles.panel}>
      <div className={styles.head}>
        <div className={styles.titles}>
          <div className={styles.sectionLabel}>Manuscript</div>
          <div className={styles.summary}>
            <span className="mono">
              {ready}/{chapters.length} chapters have text
            </span>
            {chapters.length > 0 && (
              <span className="mono">
                {chapters
                  .reduce((n, c) => n + c.text.length, 0)
                  .toLocaleString()}{" "}
                chars total
              </span>
            )}
          </div>
        </div>
        <button className="btn" onClick={onAdd} disabled={isGenerating}>
          + Add chapter
        </button>
      </div>

      {chapters.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyTitle}>No chapters yet</div>
          <div className={styles.emptyText}>
            Paste your first chapter below, then keep adding. When you are
            ready, hit <span className="mono">Generate all</span> and every
            chapter will be narrated in parallel on your GPU.
          </div>
          <button className={`btn btnPrimary ${styles.emptyBtn}`} onClick={onAdd}>
            + Add chapter 1
          </button>
        </div>
      ) : (
        <div className={styles.list}>
          {chapters.map((ch, i) => (
            <ChapterCard
              key={ch.id}
              chapter={ch}
              index={i}
              canDelete={chapters.length > 1}
              now={now}
              onUpdate={(patch) => onUpdate(ch.id, patch)}
              onDelete={() => onDelete(ch.id)}
              onRetry={() => onRetry(ch.id)}
            />
          ))}
        </div>
      )}

      {/* Action bar */}
      {chapters.length > 0 && (
        <div className={styles.actionBar}>
          {generatingAll ? (
            <ProgressBar
              completed={completed}
              total={ready}
              failed={failed}
              fraction={fraction}
              elapsedSeconds={
                jobStartedAt ? Math.floor((now - jobStartedAt) / 1000) : undefined
              }
            />
          ) : (
            <button
              className={`btn btnPrimary ${styles.generateBtn}`}
              onClick={onGenerateAll}
              disabled={isGenerating || ready === 0}
            >
              ⚡ Generate all {ready > 0 ? `(${ready})` : ""}
            </button>
          )}

          {hasResults && !isGenerating && (
            <button className="btn" onClick={onDownloadZip}>
              Download all .zip
            </button>
          )}
        </div>
      )}

      {isGenerating && (
        <p className={`mono ${styles.barHint}`}>
          Narrating chapters in parallel on GPU — you can keep editing or leave
          this tab.
        </p>
      )}
    </section>
  );
}
