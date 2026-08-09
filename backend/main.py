"""
Kokoro-82M TTS Studio — FastAPI Backend
Provides REST API endpoints for text-to-speech synthesis.
"""

import base64
import io
import logging
import re
import threading
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from voice_catalog import VOICE_CATALOG, SAMPLE_PRESETS
from models import (
    SynthesizeRequest,
    BlendRequest,
    BatchRequest,
    BatchVoice,
    Chapter,
    AudiobookRequest,
    ChapterStatus,
    AudiobookStatus,
    DeviceRequest,
    HealthResponse,
)
from tts_engine import engine, preload_voices, voice_cache_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the default English pipeline on startup."""
    logger.info("Pre-warming default pipeline (lang_code='a')...")
    engine._get_pipeline("a")
    logger.info("Pipeline ready.")
    # Download all voice packs in the background so synthesis works offline later.
    threading.Thread(target=preload_voices, daemon=True).start()
    threading.Thread(target=_job_monitor, daemon=True).start()
    yield


app = FastAPI(
    title="Kokoro-82M TTS API",
    description="High-quality local text-to-speech powered by Kokoro-82M",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Gen-Time", "X-Duration", "X-RTF", "X-Blend-Label"],
)


# ------------------------------------------------------------------
# Audiobook job manager — parallel chapter synthesis
# ------------------------------------------------------------------

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_MAX_JOBS = 50


def _sanitize_filename(name: str) -> str:
    """Make a chapter title safe for use as a file name."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    name = re.sub(r"\s+", " ", name)
    return name[:80] or "chapter"


def _audiobook_worker(idx: int, job: dict, chapter: Chapter, voice: str, lang_code: str, speed: float):
    """Synthesize one chapter inside a background job. Runs in a thread pool."""
    results: list[dict] = job["results"]
    results[idx].update({"status": "generating", "started_at": time.time(), "progress": 0.0, "audio_sec_done": 0.0})

    est_sec = results[idx].get("est_audio_sec") or 1.0

    def on_progress(audio_sec: float):
        # GIL makes these atomic dict writes safe from the polling thread
        results[idx]["audio_sec_done"] = round(audio_sec, 1)
        results[idx]["progress"] = min(1.0, audio_sec / est_sec)

    try:
        audio, phonemes, gen_time, duration = engine.synthesize(
            text=chapter.text, voice=voice, lang_code=lang_code, speed=speed,
            on_progress=on_progress,
        )
    except Exception as e:
        logger.error(f"Audiobook chapter {idx} error: {e}")
        results[idx].update({"status": "error", "error": str(e), "started_at": None})
        return

    if audio is None or len(audio) == 0:
        results[idx].update({"status": "error", "error": "No audio generated — check chapter text.", "started_at": None})
        return

    wav_bytes = engine.audio_to_wav_bytes(audio)
    rtf = gen_time / duration if duration > 0 else 0
    results[idx].update(
        {
            "status": "done",
            "started_at": None,
            "progress": 1.0,
            "gen_time": round(gen_time, 3),
            "duration": round(duration, 3),
            "rtf": round(rtf, 3),
            "phonemes": phonemes,
            "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
        }
    )


def _run_audiobook_job(job_id: str):
    """Background runner: synthesizes all chapters in parallel."""
    job = _JOBS[job_id]
    chapters: list[Chapter] = job["chapters"]
    voice = job["voice"]
    lang_code = job["lang_code"]
    speed = job["speed"]
    workers = min(job["max_workers"], len(chapters))

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_audiobook_worker, i, job, ch, voice, lang_code, speed)
                for i, ch in enumerate(chapters)
            ]
            for f in futures:
                f.result()
        with _JOBS_LOCK:
            job["status"] = "done"
    except Exception as e:
        logger.error(f"Audiobook job {job_id} failed: {e}")
        with _JOBS_LOCK:
            job["status"] = "failed"
            for res in job["results"]:
                if res["status"] in ("queued", "generating"):
                    res.update({"status": "error", "error": f"Job aborted: {e}"})


def _job_deadline(chapters: list[Chapter], workers: int) -> float:
    """Estimate how long a job may legitimately take before being marked dead."""
    total_chars = sum(len(ch.text) for ch in chapters)
    est_audio_sec = total_chars / 16.0
    rtf_estimate = 0.2 if engine.device.startswith("cuda") else 4.0
    est_sec = est_audio_sec * rtf_estimate / max(workers, 1) + 240.0
    return min(max(est_sec, 600.0), 6 * 3600.0)


def _job_monitor():
    """Watchdog: fails jobs that have run past their deadline so the UI never polls forever."""
    while True:
        time.sleep(30)
        now = time.time()
        with _JOBS_LOCK:
            for jid, job in list(_JOBS.items()):
                if job["status"] == "running" and job.get("deadline") and now > job["deadline"]:
                    logger.warning(f"Audiobook job {jid} exceeded deadline — marking failed")
                    job["status"] = "failed"
                    for res in job["results"]:
                        if res["status"] in ("queued", "generating"):
                            res.update({"status": "error", "error": "Job timed out", "started_at": None})


def _job_status_dict(job_id: str) -> dict:
    """Build the API status payload for a job."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(job_id)
        results = []
        now = time.time()
        for r in job["results"]:
            item = dict(r)
            if item["status"] == "generating" and item.get("started_at"):
                item["elapsed"] = round(now - item["started_at"], 1)
            item.pop("started_at", None)
            results.append(item)
        total = len(results)
        completed = sum(1 for r in results if r["status"] == "done")
        failed = sum(1 for r in results if r["status"] == "error")
    return {
        "job_id": job_id,
        "status": job["status"],
        "total": total,
        "completed": completed,
        "failed": failed,
        "chapters": results,
    }


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Server health check with model & hardware info."""
    total = sum(len(v["voices"]) for v in VOICE_CATALOG.values())
    return HealthResponse(
        status="online",
        model="Kokoro-82M",
        cuda_available=engine.cuda_available,
        gpu_name=engine.gpu_name,
        device=engine.device,
        total_voices=total,
    )


@app.get("/api/devices")
async def devices():
    """List selectable compute devices and the currently active one."""
    return {"devices": engine.available_devices(), "current": engine.device}


@app.post("/api/device")
async def set_device(req: DeviceRequest):
    """Switch the compute device (GPU ↔ CPU). Rejected while a job is running."""
    with _JOBS_LOCK:
        if any(job["status"] == "running" for job in _JOBS.values()):
            raise HTTPException(status_code=409, detail="Cannot switch device while a job is generating")
    try:
        engine.set_device(req.device)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    logger.info(f"Device switched to '{engine.device}'")
    return {"device": engine.device}


@app.get("/api/gpu")
async def gpu_stats():
    """Live GPU memory stats: total/free/allocated/reserved + model baseline."""
    return engine.gpu_stats()


@app.get("/api/voices")
async def get_voices():
    """Return the full voice catalog grouped by language."""
    return VOICE_CATALOG


@app.get("/api/voices/cache")
async def get_voice_cache():
    """Which voice packs are already cached locally (offline readiness)."""
    return voice_cache_status()


@app.get("/api/presets")
async def get_presets():
    """Return sample text presets."""
    return SAMPLE_PRESETS


@app.post("/api/synthesize")
async def synthesize(req: SynthesizeRequest):
    """Synthesize speech with a single voice. Returns WAV binary."""
    try:
        audio, phonemes, gen_time, duration = engine.synthesize(
            text=req.text,
            voice=req.voice,
            lang_code=req.lang_code,
            speed=req.speed,
        )
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

    if audio is None:
        raise HTTPException(status_code=422, detail="No audio generated — check your text input.")

    wav_bytes = engine.audio_to_wav_bytes(audio)
    rtf = gen_time / duration if duration > 0 else 0

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Gen-Time": f"{gen_time:.3f}",
            "X-Duration": f"{duration:.3f}",
            "X-RTF": f"{rtf:.3f}",
        },
    )


@app.post("/api/synthesize/blend")
async def synthesize_blend(req: BlendRequest):
    """Synthesize speech with a blended voice. Returns WAV binary."""
    try:
        audio, phonemes, gen_time, duration = engine.synthesize_blend(
            text=req.text,
            voice_a=req.voice_a,
            voice_b=req.voice_b,
            blend_ratio=req.blend_ratio,
            lang_code=req.lang_code,
            speed=req.speed,
        )
    except Exception as e:
        logger.error(f"Blend synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Blend synthesis failed: {str(e)}")

    if audio is None:
        raise HTTPException(status_code=422, detail="No audio generated — check your text input.")

    wav_bytes = engine.audio_to_wav_bytes(audio)
    rtf = gen_time / duration if duration > 0 else 0
    blend_label = f"{int(req.blend_ratio*100)}% {req.voice_a} + {int((1-req.blend_ratio)*100)}% {req.voice_b}"

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Gen-Time": f"{gen_time:.3f}",
            "X-Duration": f"{duration:.3f}",
            "X-RTF": f"{rtf:.3f}",
            "X-Blend-Label": blend_label,
        },
    )


@app.post("/api/synthesize/batch")
async def synthesize_batch(req: BatchRequest):
    """Synthesize speech with multiple voices for comparison. Returns JSON with base64 audio."""
    # Resolve voice labels
    lang_voices = VOICE_CATALOG.get(req.lang_code, {}).get("voices", {})
    results: list[dict] = []

    for voice_key in req.voices:
        try:
            audio, phonemes, gen_time, duration = engine.synthesize(
                text=req.text,
                voice=voice_key,
                lang_code=req.lang_code,
                speed=req.speed,
            )
        except Exception as e:
            logger.error(f"Batch synthesis error for {voice_key}: {e}")
            results.append({
                "voice": voice_key,
                "voice_label": lang_voices.get(voice_key, voice_key),
                "error": str(e),
            })
            continue

        if audio is None:
            results.append({
                "voice": voice_key,
                "voice_label": lang_voices.get(voice_key, voice_key),
                "error": "No audio generated",
            })
            continue

        wav_bytes = engine.audio_to_wav_bytes(audio)
        rtf = gen_time / duration if duration > 0 else 0

        results.append({
            "voice": voice_key,
            "voice_label": lang_voices.get(voice_key, voice_key),
            "gen_time": round(gen_time, 3),
            "duration": round(duration, 3),
            "rtf": round(rtf, 3),
            "phonemes": phonemes,
            "audio_base64": base64.b64encode(wav_bytes).decode("utf-8"),
        })

    return {"results": results}


# ------------------------------------------------------------------
# Audiobook endpoints
# ------------------------------------------------------------------

@app.post("/api/audiobook/generate")
async def audiobook_generate(req: AudiobookRequest):
    """Start parallel synthesis of all chapters. Returns a job_id for polling."""
    job_id = uuid.uuid4().hex[:12]

    results = [
        {
            "title": ch.title,
            "status": "queued",
            "error": None,
            "started_at": None,
            "est_audio_sec": round(engine.estimate_audio_sec(ch.text), 1),
            "progress": 0.0,
            "audio_sec_done": 0.0,
            "gen_time": None,
            "duration": None,
            "rtf": None,
            "phonemes": None,
            "audio_base64": None,
        }
        for ch in req.chapters
    ]

    with _JOBS_LOCK:
        if len(_JOBS) >= _MAX_JOBS:
            oldest = next(iter(_JOBS))
            del _JOBS[oldest]
        _JOBS[job_id] = {
            "status": "running",
            "chapters": list(req.chapters),
            "results": results,
            "voice": req.voice,
            "lang_code": req.lang_code,
            "speed": req.speed,
            "max_workers": req.max_workers,
            "deadline": time.time() + _job_deadline(req.chapters, req.max_workers),
        }

    logger.info(
        f"Audiobook job {job_id} started: {len(req.chapters)} chapters, "
        f"voice={req.voice}, lang={req.lang_code}, workers={req.max_workers}"
    )
    threading.Thread(target=_run_audiobook_job, args=(job_id,), daemon=True).start()

    return {"job_id": job_id, "total": len(req.chapters)}


@app.get("/api/audiobook/status/{job_id}", response_model=AudiobookStatus)
async def audiobook_status(job_id: str):
    """Poll the progress of an audiobook job (per-chapter status + base64 WAVs when done)."""
    try:
        return _job_status_dict(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/audiobook/download/{job_id}")
async def audiobook_download(job_id: str):
    """Download all generated chapters as a single ZIP file."""
    try:
        payload = _job_status_dict(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")

    done = [c for c in payload["chapters"] if c.get("status") == "done"]
    if not done:
        raise HTTPException(status_code=422, detail="No completed chapters to download")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, ch in enumerate(done):
            name = _sanitize_filename(ch.get("title") or f"Chapter {i + 1}")
            if not name.lower().endswith(".wav"):
                name += ".wav"
            wav_bytes = base64.b64decode(ch["audio_base64"])
            zf.writestr(name, wav_bytes)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="audiobook_{job_id}.zip"'},
    )
