"""
TTS Engine wrapper around Kokoro KPipeline.
Handles model loading, caching, and audio generation.
"""

import io
import time
import torch
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TTSEngine:
    """Manages Kokoro TTS pipeline instances with caching per language+device."""

    def __init__(self):
        self._pipelines: dict[str, KPipeline] = {}
        self._device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self._gpu_name: Optional[str] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        )
        self._base_bytes: Optional[int] = None  # GPU bytes allocated by the model itself
        logger.info(f"TTS Engine initialized — device: {self._device}, GPU: {self._gpu_name}")

    @property
    def device(self) -> str:
        return self._device

    @property
    def gpu_name(self) -> Optional[str]:
        return self._gpu_name

    @property
    def cuda_available(self) -> bool:
        return torch.cuda.is_available()

    def available_devices(self) -> list[dict]:
        """List selectable compute devices (GPUs + CPU fallback)."""
        devices = []
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            for i in range(count):
                name = torch.cuda.get_device_name(i)
                devices.append({
                    "device": f"cuda:{i}" if count > 1 else "cuda",
                    "label": f"GPU — {name}",
                })
        devices.append({"device": "cpu", "label": "CPU"})
        return devices

    def set_device(self, device: str) -> None:
        """Switch the compute device used for synthesis. Clears cached pipelines."""
        valid = {d["device"] for d in self.available_devices()}
        if device not in valid:
            raise ValueError(f"Unsupported device: {device}")
        if device == self._device:
            return
        self._pipelines.clear()
        if self.cuda_available:
            torch.cuda.empty_cache()
        self._device = device
        self._base_bytes = None
        if device.startswith("cuda"):
            idx = int(device.split(":")[-1]) if ":" in device else 0
            self._gpu_name = torch.cuda.get_device_name(idx)
        else:
            self._gpu_name = None
        logger.info(f"Switched compute device to '{device}'")

    def _get_pipeline(self, lang_code: str) -> KPipeline:
        """Get or create a cached pipeline for the given language."""
        cache_key = f"{lang_code}_{self._device}"
        if cache_key not in self._pipelines:
            logger.info(f"Loading pipeline: lang={lang_code}, device={self._device}")
            self._pipelines[cache_key] = KPipeline(lang_code=lang_code, device=self._device)
            if self.cuda_available:
                torch.cuda.synchronize()
                self._base_bytes = torch.cuda.memory_allocated()
        return self._pipelines[cache_key]

    def gpu_stats(self) -> dict:
        """Live GPU memory stats (total/free/allocated/reserved + model baseline)."""
        if not self.cuda_available:
            return {
                "cuda_available": False,
                "device": self._device,
                "gpu_name": None,
                "total_bytes": None,
                "free_bytes": None,
                "allocated_bytes": None,
                "reserved_bytes": None,
                "base_bytes": None,
            }
        free, total = torch.cuda.mem_get_info()
        return {
            "cuda_available": True,
            "device": self._device,
            "gpu_name": self._gpu_name,
            "total_bytes": total,
            "free_bytes": free,
            "allocated_bytes": torch.cuda.memory_allocated(),
            "reserved_bytes": torch.cuda.memory_reserved(),
            "base_bytes": self._base_bytes,
        }

    @staticmethod
    def estimate_audio_sec(text: str) -> float:
        """Best-effort estimate of narrated audio length (~16 chars per second)."""
        return max(0.0, len(text.strip()) / 16.0)

    def synthesize(
        self,
        text: str,
        voice: str,
        lang_code: str = "a",
        speed: float = 1.0,
        on_progress: Optional[callable] = None,
    ) -> tuple[Optional[np.ndarray], str, float, float]:
        """
        Synthesize speech from text using a single voice.

        on_progress: optional callback invoked after every inference pass with
        the cumulative audio seconds generated so far (progress signal).

        Returns:
            (audio_array, phonemes, gen_time_sec, duration_sec)
        """
        pipeline = self._get_pipeline(lang_code)
        t0 = time.time()
        generator = pipeline(text, voice=voice, speed=speed)
        all_audio = []
        all_phonemes = []
        total_samples = 0

        for _gs, ps, audio in generator:
            if audio is not None and len(audio) > 0:
                # Move off the GPU immediately so long chapters don't pin VRAM
                total_samples += len(audio)
                all_audio.append(audio.cpu().numpy())
                if on_progress is not None:
                    on_progress(total_samples / 24000.0)
            if ps:
                all_phonemes.append(ps)

        gen_time = time.time() - t0

        if not all_audio:
            return None, "", 0.0, 0.0

        full_audio = np.concatenate(all_audio)
        phonemes_str = " | ".join(all_phonemes)
        duration_sec = len(full_audio) / 24000.0
        return full_audio, phonemes_str, gen_time, duration_sec

    def synthesize_blend(
        self,
        text: str,
        voice_a: str,
        voice_b: str,
        blend_ratio: float = 0.7,
        lang_code: str = "a",
        speed: float = 1.0,
    ) -> tuple[Optional[np.ndarray], str, float, float]:
        """
        Synthesize speech using a blended voice (weighted mix of two voices).
        
        Returns:
            (audio_array, phonemes, gen_time_sec, duration_sec)
        """
        pipeline = self._get_pipeline(lang_code)
        v1 = pipeline.load_voice(voice_a)
        v2 = pipeline.load_voice(voice_b)
        blended = blend_ratio * v1 + (1.0 - blend_ratio) * v2
        return self.synthesize(text, voice=blended, lang_code=lang_code, speed=speed)

    @staticmethod
    def audio_to_wav_bytes(audio_array: np.ndarray, sample_rate: int = 24000) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        buf = io.BytesIO()
        sf.write(buf, audio_array, sample_rate, format="WAV")
        return buf.getvalue()


# Singleton instance — created once at import time
engine = TTSEngine()
