"""Decode, resample, encode and describe audio. Everything works on mono float32 samples."""
from __future__ import annotations

import io
import os
import wave
from dataclasses import dataclass

import lameenc
import miniaudio
import numpy as np

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.flac', '.ogg')
STANDARD_BITRATES = (32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256)


@dataclass
class Audio:
    samples: np.ndarray  # float32, mono, -1..1
    sr: int

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sr


def file_info(path: str) -> miniaudio.SoundFileInfo:
    return miniaudio.get_file_info(path)


def load(path: str, sr: int | None = None) -> Audio:
    """Decode a file to mono float32. With `sr` the decoder resamples to that rate; otherwise the file's own rate is kept."""
    rate = sr or file_info(path).sample_rate
    d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1, sample_rate=rate)
    return Audio(np.frombuffer(d.samples, dtype=np.float32).copy(), rate)


def load_bytes(data: bytes, suffix: str = '.mp3', sr: int | None = None) -> Audio:
    """Decode audio held in memory (the decoder wants a file, so this goes through a temporary one)."""
    import tempfile

    fd, tmp = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        return load(tmp, sr)
    finally:
        os.unlink(tmp)


def to_16k(a: Audio) -> np.ndarray:
    """What speech recognition wants: 16 kHz mono float32."""
    if a.sr == 16000:
        return a.samples
    n = int(round(len(a.samples) * 16000 / a.sr))
    return np.interp(np.linspace(0, len(a.samples) - 1, n), np.arange(len(a.samples)), a.samples).astype(np.float32)


def guess_bitrate(path: str, duration: float) -> int:
    """The nearest standard MP3 bitrate (kbps) for a file, from its size."""
    if duration <= 0:
        return 64
    kbps = os.path.getsize(path) * 8 / duration / 1000
    return min(STANDARD_BITRATES, key=lambda b: abs(b - kbps))


def encode_mp3(samples: np.ndarray, sr: int, bitrate: int = 64) -> bytes:
    enc = lameenc.Encoder()
    enc.set_bit_rate(bitrate)
    enc.set_in_sample_rate(sr)
    enc.set_out_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype('<i2').tobytes()
    return bytes(enc.encode(pcm)) + bytes(enc.flush())


def to_wav_bytes(samples: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype('<i2').tobytes())
    return buf.getvalue()


def peaks(samples: np.ndarray, buckets: int) -> list[list[float]]:
    """(min, max) per bucket, for drawing a waveform."""
    n = len(samples)
    if n == 0 or buckets <= 0:
        return []
    edges = np.linspace(0, n, buckets + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = samples[a:max(b, a + 1)]
        out.append([round(float(seg.min()), 4), round(float(seg.max()), 4)])
    return out
