"use client";

import { HealthInfo } from "@/lib/api";
import styles from "./Header.module.css";

interface HeaderProps {
  health: HealthInfo | null;
}

export default function Header({ health }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <div className={styles.wordmark}>Narrate</div>
        <div className={styles.tagline}>Local audiobook studio</div>
      </div>

      {health ? (
        <div className={styles.badges}>
          <span className={styles.badge}>
            <span className={`${styles.dot} ${styles.dotGreen}`} />
            {health.model}
          </span>
          {health.cuda_available && health.gpu_name ? (
            <span className={styles.badge} title={health.gpu_name}>
              <span className={`${styles.dot} ${styles.dotWhite}`} />
              GPU
            </span>
          ) : (
            <span className={styles.badge}>
              <span className={`${styles.dot} ${styles.dotGray}`} />
              CPU
            </span>
          )}
          <span className={styles.badge}>{health.sample_rate / 1000}kHz</span>
          <span className={styles.badge}>{health.total_voices} voices</span>
        </div>
      ) : (
        <div className={styles.loading}>
          <span className="spinner" />
          <span className="mono">connecting…</span>
        </div>
      )}
    </header>
  );
}
