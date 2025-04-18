from __future__ import annotations

import asyncio
import base64
import io
import wave
from dataclasses import dataclass

from ..exceptions import UserError
from .imports import np, npt

DEFAULT_SAMPLE_RATE = 24000


def _buffer_to_audio_file(
    buffer: npt.NDArray[np.int16 | np.float32],
    frame_rate: int = DEFAULT_SAMPLE_RATE,
    sample_width: int = 2,
    channels: int = 1,
) -> tuple[str, io.BytesIO, str]:
    if buffer.dtype == np.float32:
        # convert to int16
        buffer = np.clip(buffer, -1.0, 1.0)
        buffer = (buffer * 32767).astype(np.int16)
    elif buffer.dtype != np.int16:
        raise UserError("Buffer must be a numpy array of int16 or float32")

    audio_file = io.BytesIO()
    with wave.open(audio_file, "w") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(buffer.tobytes())
        audio_file.seek(0)

    return ("audio.wav", audio_file, "audio/wav")


@dataclass
class AudioInput:
    """Static audio to be used as input for the VoicePipeline."""

    buffer: npt.NDArray[np.int16 | np.float32]
    frame_rate: int = DEFAULT_SAMPLE_RATE
    sample_width: int = 2
    channels: int = 1

    def to_audio_file(self) -> tuple[str, io.BytesIO, str]:
        return _buffer_to_audio_file(self.buffer, self.frame_rate, self.sample_width, self.channels)

    def to_base64(self) -> str:
        if self.buffer.dtype == np.float32:
            self.buffer = np.clip(self.buffer, -1.0, 1.0)
            self.buffer = (self.buffer * 32767).astype(np.int16)
        elif self.buffer.dtype != np.int16:
            raise UserError("Buffer must be a numpy array of int16 or float32")

        return base64.b64encode(self.buffer.tobytes()).decode("utf-8")

    # ✅ This is the method you need to add for GPT-4o voice streaming to work
    @classmethod
    def from_raw_bytes(cls, raw_bytes: bytes, sample_rate: int = 8000) -> "AudioInput":
        print("📦 DEBUG: from_raw_bytes called inside AudioInput")  # Optional debug
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16)
        return cls(buffer=audio_np, frame_rate=sample_rate)


class StreamedAudioInput:
    """Audio input represented as a stream of audio data. Used in streaming voice mode."""

    def __init__(self):
        self.queue: asyncio.Queue[npt.NDArray[np.int16 | np.float32]] = asyncio.Queue()

    async def add_audio(self, audio: npt.NDArray[np.int16 | np.float32]):
        await self.queue.put(audio)
