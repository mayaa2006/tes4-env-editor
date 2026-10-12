import json
import math
from pathlib import Path

import numpy as np
import pytest

from wordsplice import audio
from wordsplice.app import App

SR = 22050


def tone(freq: float, seconds: float, amp: float = 0.4) -> np.ndarray:
    t = np.arange(int(SR * seconds)) / SR
    env = np.minimum(1, np.minimum(t, seconds - t) / 0.01)  # soft edges
    return (amp * env * np.sin(2 * math.pi * freq * t)).astype(np.float32)


def gap(seconds: float) -> np.ndarray:
    return np.zeros(int(SR * seconds), dtype=np.float32)


def make_line(words: list[tuple[str, float]], pause: float = 0.15):
    """A fake spoken line: one tone burst per word. Returns (samples, [{text,start,end}])."""
    parts, timing, t = [gap(0.1)], [], 0.1
    for text, freq in words:
        d = 0.3
        parts += [tone(freq, d), gap(pause)]
        timing.append({'text': text, 'start': round(t, 3), 'end': round(t + d, 3)})
        t += d + pause
    return np.concatenate(parts), timing


@pytest.fixture
def workspace(tmp_path: Path):
    """An app with one fake line 'Tell Martin he is late' already 'listened to' (cache pre-filled)."""
    lines = tmp_path / 'lines' / 'sound' / 'voice' / 'oblivion.esm' / 'breton' / 'm'
    lines.mkdir(parents=True)
    samples, timing = make_line([('Tell', 300), ('Martin,', 400), ('he', 500), ('is', 600), ('late.', 700)])
    path = lines / 'q_topic_00000001_1.mp3'
    path.write_bytes(audio.encode_mp3(samples, SR, 64))
    app = App(tmp_path / 'lines', tmp_path / 'work')
    app.aligner._cache_file(str(path)).write_text(json.dumps({'model': 'base.en', 'words': timing}))
    return app, 'sound/voice/oblivion.esm/breton/m/q_topic_00000001_1.mp3', tmp_path


def wav_clip(freq: float, seconds: float = 0.35, amp: float = 0.3) -> bytes:
    return audio.to_wav_bytes(np.concatenate([gap(0.05), tone(freq, seconds, amp), gap(0.05)]), SR)
