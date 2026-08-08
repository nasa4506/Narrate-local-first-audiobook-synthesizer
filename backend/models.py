"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class SynthesizeRequest(BaseModel):
    """Request body for single-voice TTS synthesis."""
    text: str = Field(..., min_length=1, max_length=100000, description="Text to synthesize")
    voice: str = Field(..., description="Voice key, e.g. 'af_heart'")
    lang_code: str = Field(default="a", description="Language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")


class BlendRequest(BaseModel):
    """Request body for blended voice TTS synthesis."""
    text: str = Field(..., min_length=1, max_length=100000, description="Text to synthesize")
    voice_a: str = Field(..., description="Primary voice key")
    voice_b: str = Field(..., description="Secondary voice key")
    blend_ratio: float = Field(default=0.7, ge=0.0, le=1.0, description="Blend ratio (0=all B, 1=all A)")
    lang_code: str = Field(default="a", description="Language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")


class BatchVoice(BaseModel):
    """Single result in a batch synthesis response."""
    voice: str
    voice_label: str
    gen_time: float
    duration: float
    rtf: float
    phonemes: str
    audio_base64: str


class BatchRequest(BaseModel):
    """Request body for multi-voice comparison synthesis."""
    text: str = Field(..., min_length=1, max_length=100000, description="Text to synthesize")
    voices: list[str] = Field(..., min_length=1, max_length=10, description="List of voice keys")
    lang_code: str = Field(default="a", description="Language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")


class Chapter(BaseModel):
    """A single chapter of an audiobook."""
    title: str = Field(default="", max_length=200, description="Chapter title (used for the output file name)")
    text: str = Field(..., min_length=1, max_length=100000, description="Chapter text to narrate")


class AudiobookRequest(BaseModel):
    """Request body for parallel multi-chapter audiobook synthesis."""
    chapters: list[Chapter] = Field(..., min_length=1, max_length=50, description="List of chapters")
    voice: str = Field(..., description="Voice key, e.g. 'af_heart'")
    lang_code: str = Field(default="a", description="Language code")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    max_workers: int = Field(default=4, ge=1, le=16, description="Max chapters synthesized in parallel")


class ChapterStatus(BaseModel):
    """Runtime status for a single chapter inside an audiobook job."""
    title: str = ""
    status: str = "queued"  # queued | generating | done | error
    error: Optional[str] = None
    elapsed: Optional[float] = None  # seconds spent generating (running chapters)
    est_audio_sec: Optional[float] = None  # estimated audio length of the chapter
    progress: Optional[float] = None  # 0..1 — audio generated so far / estimate
    audio_sec_done: Optional[float] = None  # actual audio seconds produced so far
    gen_time: Optional[float] = None
    duration: Optional[float] = None
    rtf: Optional[float] = None
    phonemes: Optional[str] = None
    audio_base64: Optional[str] = None


class AudiobookStatus(BaseModel):
    """Aggregate status of a running/finished audiobook job."""
    job_id: str
    status: str  # running | done | failed
    total: int
    completed: int
    failed: int
    chapters: list[ChapterStatus]


class DeviceRequest(BaseModel):
    """Request body for switching the compute device."""
    device: str = Field(..., description="Device to use, e.g. 'cuda', 'cuda:1' or 'cpu'")


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""
    status: str
    model: str
    cuda_available: bool
    gpu_name: Optional[str] = None
    device: str = "cpu"
    sample_rate: int = 24000
    total_voices: int
