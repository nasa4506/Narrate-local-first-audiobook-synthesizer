# Narrate — User Guide

A complete walkthrough: setup, creating an audiobook, and troubleshooting.

## 1. First-Time Setup

### 1.1 Install the backend

```bash
cd backend
pip install -r requirements.txt
```

This installs FastAPI, uvicorn, torch, numpy, soundfile, and kokoro. Torch will pull the CUDA build if available on your system (see Troubleshooting if you need a specific CUDA version).

### 1.2 Start the backend

```bash
python -m uvicorn main:app --port 8000
```

On the first start the backend downloads the **Kokoro-82M model** (~330 MB) and any voice packs from HuggingFace. This happens once — afterwards everything is cached and fully offline. You should see:

```
INFO:main:Pipeline ready.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 1.3 Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. The header should show the model badge and a **GPU** badge. If it shows a red banner, the backend isn't reachable — the app retries automatically every 5 seconds, so just start the backend and wait.

## 2. Creating Your First Audiobook

### 2.1 Add chapters

1. Click **+ Add chapter**. A chapter card appears.
2. Paste the chapter text into the textarea.
3. Give it a **title** (used for the ZIP file names) and optionally change the **File name** — this is exactly what your `.wav` will be called when you download it (`.wav` is appended automatically).
4. Repeat for each chapter. You can collapse cards with **+ / −** and delete with **×**.

> Tip: the sidebar shows `N/N chapters have text` and total character count. Only chapters with text participate in generation.

### 2.2 Pick the narrator

In the sidebar:

- **Compute device** — auto-detected on startup (GPU if an NVIDIA GPU is present, otherwise CPU). Switch anytime; the device dropdown is disabled while a job is generating. After switching, the model reloads on the new device (a few seconds on first switch).
- **Language** — region/voice family
- **Voice** — e.g. `af_heart` (Female, Clear & Expressive) or `am_adam` (Male, Deep)
- **Speed** — 0.50× to 2.00×
- **Parallel chapters** — how many chapters synthesize at once (1–8). Keep this at 2–4 for a laptop GPU, 1 for CPU.

### 2.3 Read the GPU meter

The **GPU memory** box shows two modes:

- **estimate** (idle): `est. peak = model base + N×work`, where N = how many of your chapters would run concurrently. It updates the moment you add or remove chapters.
- **live** (while generating): real `allocated / reserved` VRAM, refreshed every 2 seconds.

The bar turns **amber at 75%** and **pulsing red at 90%** of your VRAM — lower "Parallel chapters" if you see red.

### 2.4 Generate

Click **⚡ Generate all (N)**. Watch:

- Each chapter card shows a determinate **progress bar** + `synthesizing on GPU · 47% · 0:45 elapsed · est. 33:26 audio`
- The top progress bar shows the overall book progress, e.g. `2/5 chapters · 41%` with total elapsed time
- The GPU meter switches to live VRAM

### 2.5 Download

When a chapter finishes, it expands with a player and a **Download .wav** button (uses your custom file name). When everything is done, use **Download all .zip** to grab the whole audiobook.

Failed chapters show a **Retry** button — it re-narrates just that one.

## 3. Persistence & Refreshing

Everything is saved to your browser's localStorage:

- Chapter text, titles, and file names
- Narrator settings (language, voice, speed, parallel workers)
- The last completed job's ZIP link
- An **in-flight job**: refresh while generating, and the app reconnects to the backend job and keeps showing progress

> Audio players themselves don't survive a refresh (browser object URLs) — use **Download all .zip** before reloading, or regenerate after.

## 4. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot reach the TTS backend` | Start the backend (`python -m uvicorn main:app --port 8000`) — the UI reconnects automatically |
| `Port 8000 already in use` | An old instance is running: `Ctrl+C` it, or on Windows kill it with `taskkill /F /IM python.exe`, then restart |
| `The previous generation job is no longer available` | The backend was restarted mid-job (jobs are in-memory). Your text is safe — press **Generate all** again |
| Generation is very slow | You're on CPU, or too many parallel workers on a small GPU. Lower **Parallel chapters** to 1–2, or switch to GPU in **Compute device** (check the header badge) |
| No GPU badge in the header | The machine has no CUDA GPU — CPU mode is active (works, ~20–50× slower). The GPU meter shows "CPU mode" |
| `Cannot switch device while a job is generating` | Wait for the current job to finish, then switch devices |
| `CUDA out of memory` | Lower **Parallel chapters**; the GPU meter should show near-base usage with 1 worker |
| Chapter stuck at `queued` | Queued chapters wait for a free worker — they start as soon as one finishes |
| First-run download fails | Check internet access; retry once (downloads are resumable via the HuggingFace cache) |
| `'voices/…pt' is not cached locally and could not be downloaded` | That voice was never downloaded and you're offline. Run once with internet (the backend preloads **all 41 voices** at startup), or check readiness at `http://localhost:8000/api/voices/cache` |
| Offline usage | The model (312 MB) and all preloaded voices are cached under `~/.cache/huggingface/` — after one online run, synthesis works fully offline |
| Text rejected with "String should have at most 100000 characters" | Chapters are capped at 100,000 chars — split the chapter in two |
| Hydration error in console | Hard-refresh (Ctrl+Shift+R); this was a known issue fixed by deferring localStorage restore until after hydration |

## 5. Voice Reference

Common voices (US English, `lang_code: a`):

| Voice | Character |
| --- | --- |
| `af_heart` | Female — Heart (clear, expressive, default) |
| `af_bella` | Female — Bella (warm, gentle) |
| `af_nicole` | Female — Nicole (casual) |
| `af_sarah` | Female — Sarah (bright) |
| `am_adam` | Male — Adam (deep, authoritative) |
| `am_michael` | Male — Michael (friendly) |
| `am_onyx` | Male — Onyx (deep) |

British (`b`): `bf_emma`, `bf_isabella`, `bm_george`, `bm_daniel` … Spanish (`e`), French (`f`), Hindi (`h`), Italian (`i`), Portuguese (`p`) voice families are also available.
