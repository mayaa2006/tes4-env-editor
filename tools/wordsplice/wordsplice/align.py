"""Find where each word is spoken in a line.

A small speech model (faster-whisper) listens to the line and reports every word with start and end times.
Results are kept next to your work, so each line is only listened to once.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import numpy as np

from . import audio
from .rules import norm
from .splice import snap


class AlignUnavailable(RuntimeError):
    pass


class Aligner:
    def __init__(self, cache_dir: Path, model: str = 'base.en'):
        self.cache_dir = cache_dir
        self.model_name = model
        self._model = None
        self._lock = threading.Lock()
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_file(self, path: str) -> Path:
        h = hashlib.sha1(Path(path).read_bytes()).hexdigest()
        return self.cache_dir / f'{h}-{self.model_name}.json'

    def cached(self, path: str) -> bool:
        return self._cache_file(path).exists()

    def cached_words(self, path: str) -> list[dict] | None:
        f = self._cache_file(path)
        return json.loads(f.read_text(encoding='utf8'))['words'] if f.exists() else None

    def available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def words(self, path: str, a: audio.Audio, hint: str = '') -> list[dict]:
        """[{text, start, end}] in seconds, from the cache or by listening to the line."""
        f = self._cache_file(path)
        if f.exists():
            return json.loads(f.read_text(encoding='utf8'))['words']
        with self._lock:
            if self._model is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as e:
                    raise AlignUnavailable('Automatic word finding needs faster-whisper (pip install faster-whisper).') from e
                self._model = WhisperModel(self.model_name, device='cpu', compute_type='int8')
            segments, _ = self._model.transcribe(
                audio.to_16k(a), language='en', word_timestamps=True, beam_size=5,
                condition_on_previous_text=False, initial_prompt=hint or None,
            )
            words = [{'text': w.word.strip(), 'start': round(float(w.start), 3), 'end': round(float(w.end), 3)} for s in segments for w in (s.words or [])]
        f.write_text(json.dumps({'model': self.model_name, 'words': words}, ensure_ascii=False), encoding='utf8')
        return words


def snapped_words(words: list[dict], a: audio.Audio) -> list[dict]:
    """Move each word's edges to the nearest quiet spot so a cut doesn't click, keeping words in order."""
    out, prev_end = [], 0
    for i, w in enumerate(words):
        s = max(snap(a.samples, a.sr, w['start']), prev_end)
        e = max(snap(a.samples, a.sr, w['end']), s + 1)
        out.append({'i': i, 'text': w['text'], 'norm': norm(w['text']), 'start': round(s / a.sr, 4), 'end': round(e / a.sr, 4)})
        prev_end = e
    return out
