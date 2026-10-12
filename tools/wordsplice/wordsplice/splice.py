"""The splice itself: trim and level a replacement clip, then cross-fade it into the line."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

FADE_MS = 8.0


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def trim_silence(x: np.ndarray, sr: int, thresh_db: float = -45.0, pad_ms: float = 4.0) -> np.ndarray:
    """Cut quiet lead-in and tail from a recorded clip, keeping a few ms so the word doesn't start abruptly."""
    if not len(x):
        return x
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        return x
    loud = np.nonzero(np.abs(x) > peak * 10 ** (thresh_db / 20))[0]
    pad = int(sr * pad_ms / 1000)
    return x[max(0, loud[0] - pad): min(len(x), loud[-1] + pad + 1)]


def snap(x: np.ndarray, sr: int, t: float, window: float = 0.06, frame_ms: float = 4.0) -> int:
    """The sample index near time `t` where the sound is quietest (best place to cut without a click)."""
    n = len(x)
    centre = min(max(int(round(t * sr)), 0), n)
    frame = max(1, int(sr * frame_ms / 1000))
    lo, hi = max(0, centre - int(window * sr)), min(n, centre + int(window * sr))
    if hi - lo < 2 * frame:
        return centre
    seg = np.abs(x[lo:hi])
    energy = np.convolve(seg, np.ones(frame) / frame, mode='same')
    # Prefer the quietest spot, but among near-equal ones the closest to where the recogniser put the boundary.
    floor = float(energy.min())
    ok = np.nonzero(energy <= floor + 0.03 * (float(energy.max()) - floor) + 1e-9)[0]
    best = ok[np.argmin(np.abs((ok + lo) - centre))]
    return int(lo + best)


def match_level(clip: np.ndarray, reference: np.ndarray, max_db: float = 12.0) -> np.ndarray:
    """Scale `clip` so its loudness matches `reference`, never more than `max_db` and never into clipping."""
    r_clip, r_ref = rms(clip), rms(reference)
    if r_clip <= 1e-6 or r_ref <= 1e-6:
        return clip
    gain_db = max(-max_db, min(max_db, 20 * math.log10(r_ref / r_clip)))
    out = clip * (10 ** (gain_db / 20))
    peak = float(np.max(np.abs(out))) if len(out) else 0.0
    return out / peak * 0.98 if peak > 0.98 else out


def crossfade_join(a: np.ndarray, b: np.ndarray, n: int) -> np.ndarray:
    """Join `a` and `b` with an equal-power cross-fade over up to `n` samples."""
    n = max(0, min(n, len(a), len(b)))
    if n == 0:
        return np.concatenate([a, b])
    t = np.linspace(0.0, math.pi / 2, n, dtype=np.float32)
    mixed = a[len(a) - n:] * np.cos(t) + b[:n] * np.sin(t)
    return np.concatenate([a[:len(a) - n], mixed.astype(np.float32), b[n:]])


@dataclass
class Edit:
    start: int  # sample index where the original word starts
    end: int  # sample index where it ends
    clip: np.ndarray  # replacement, already trimmed, levelled and at the line's sample rate


def prepare(clip: np.ndarray, original_word: np.ndarray, sr: int) -> np.ndarray:
    return match_level(trim_silence(clip, sr), original_word)


def apply_edits(x: np.ndarray, edits: list[Edit], sr: int, fade_ms: float = FADE_MS) -> np.ndarray:
    """Replace each [start, end) of `x` with its clip. Edits may not overlap."""
    fade = max(1, int(sr * fade_ms / 1000))
    out = np.zeros(0, dtype=np.float32)
    pos = 0
    for e in sorted(edits, key=lambda e: e.start):
        if e.start < pos or e.end < e.start or e.end > len(x):
            raise ValueError('Edits overlap or run outside the line')
        out = crossfade_join(out, x[pos:e.start], fade) if len(out) else x[pos:e.start]
        out = crossfade_join(out, e.clip.astype(np.float32), fade) if len(out) else e.clip.astype(np.float32)
        pos = e.end
    tail = x[pos:]
    return crossfade_join(out, tail, fade) if len(out) and len(tail) else np.concatenate([out, tail]).astype(np.float32)
