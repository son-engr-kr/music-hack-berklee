"""Shared Magenta RT 2 engine — loads model once, shared across all modes."""

import time
import threading
import io
import struct
import logging

import numpy as np

from magenta_rt import MagentaRT2Mlxfn, audio

logger = logging.getLogger(__name__)


_NOTES_MASKED = [-1] * 128


def _notes_for_pitch(pitch: int, velocity: int = 100) -> list[int]:
    notes = _NOTES_MASKED[:]
    if 0 <= pitch < 128:
        notes[pitch] = 3
    return notes


def _wav_to_bytes(wav: audio.Waveform) -> bytes:
    """Convert Waveform to WAV bytes for streaming."""
    samples = wav.samples
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]
    n_channels = samples.shape[1]
    sample_rate = wav.sample_rate
    bits_per_sample = 16
    n_samples = samples.shape[0]

    data = (samples * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
    data_size = len(data)

    buf = io.BytesIO()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))
    buf.write(struct.pack('<H', 1))
    buf.write(struct.pack('<H', n_channels))
    buf.write(struct.pack('<I', sample_rate))
    buf.write(struct.pack('<I', sample_rate * n_channels * bits_per_sample // 8))
    buf.write(struct.pack('<H', n_channels * bits_per_sample // 8))
    buf.write(struct.pack('<H', bits_per_sample))
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(data)

    return buf.getvalue()


class MRT2Engine:
    """Singleton engine — one model instance shared across all modes."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_size: str = "mrt2_small", temperature: float = 1.2):
        self.model_size = model_size
        self.temperature = temperature
        self._states: dict[str, any] = {}
        self._style_cache: dict[str, any] = {}

        logger.info("Loading Magenta RT 2 (%s)...", model_size)
        self._mrt = MagentaRT2Mlxfn(
            size=model_size,
            temperature=temperature,
        )
        logger.info("Engine ready.")

    @classmethod
    def get_instance(cls, model_size: str = "mrt2_small") -> "MRT2Engine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_size=model_size)
        return cls._instance

    def get_style(self, prompt: str):
        if prompt not in self._style_cache:
            self._style_cache[prompt] = self._mrt.embed_style(prompt)
        return self._style_cache[prompt]

    def generate(
        self,
        prompt: str,
        session_id: str = "default",
        notes: list[int] | None = None,
        drums: list[int] | None = None,
        frames: int = 25,
    ) -> bytes:
        style = self.get_style(prompt)
        prev_state = self._states.get(session_id)

        wav, new_state = self._mrt.generate(
            style=style,
            notes=notes if notes is not None else _NOTES_MASKED,
            drums=drums if drums is not None else [-1],
            frames=frames,
            state=prev_state,
        )

        self._states[session_id] = new_state
        return _wav_to_bytes(wav)

    def reset_session(self, session_id: str):
        self._states.pop(session_id, None)

    @property
    def sample_rate(self) -> int:
        return self._mrt._sample_rate
