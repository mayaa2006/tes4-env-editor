"""The bank of clips you provide: a folder per word, any number of clips per word.

    bank/she/warm.wav
    bank/she/flat.mp3
    bank/ariella/take1.wav
    bank/bank.json       (optional labels and voice tags, written by the app)
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from . import audio
from .rules import norm, valid_word
from .splice import rms, trim_silence


@dataclass
class Variant:
    id: str  # "she/warm.wav"
    word: str
    file: str
    label: str
    voice: str  # e.g. "breton/m", or "" for any voice
    duration: float
    level: float  # RMS of the spoken part


class Bank:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._meta_path = root / 'bank.json'
        self._cache: dict[str, audio.Audio] = {}

    def _meta(self) -> dict[str, dict[str, str]]:
        return json.loads(self._meta_path.read_text(encoding='utf8')) if self._meta_path.exists() else {}

    def _save_meta(self, meta: dict) -> None:
        self._meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf8')

    def variants(self) -> dict[str, list[Variant]]:
        meta = self._meta()
        out: dict[str, list[Variant]] = {}
        for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
            word = norm(d.name)
            for f in sorted(d.iterdir()):
                if f.suffix.lower() not in audio.AUDIO_EXTENSIONS:
                    continue
                vid = f'{d.name}/{f.name}'
                m = meta.get(vid, {})
                a = self.get(vid)
                spoken = trim_silence(a.samples, a.sr)
                out.setdefault(word, []).append(Variant(vid, word, f.name, m.get('label', f.stem), m.get('voice', ''), round(a.duration, 3), round(rms(spoken), 4)))
        return out

    def get(self, variant_id: str, sr: int | None = None) -> audio.Audio:
        """Decode a clip (at `sr` if given), cached."""
        key = f'{variant_id}@{sr or 0}'
        if key not in self._cache:
            path = (self.root / variant_id).resolve()
            if self.root.resolve() not in path.parents or not path.is_file():
                raise FileNotFoundError(f'No clip "{variant_id}" in the bank')
            self._cache[key] = audio.load(str(path), sr)
        return self._cache[key]

    def add(self, word: str, filename: str, data: bytes, label: str = '', voice: str = '') -> Variant:
        w = norm(word)
        if not valid_word(w):
            raise ValueError(f'"{word}" is not a word the bank can use (letters, numbers, apostrophes and hyphens)')
        suffix = Path(filename).suffix.lower()
        if suffix not in audio.AUDIO_EXTENSIONS:
            raise ValueError(f'Clips must be {", ".join(audio.AUDIO_EXTENSIONS)} files')
        stem = re.sub(r'[^A-Za-z0-9_\- ]+', '_', Path(filename).stem).strip() or 'clip'
        folder = self.root / w
        folder.mkdir(exist_ok=True)
        target, n = folder / f'{stem}{suffix}', 2
        while target.exists():
            target, n = folder / f'{stem}-{n}{suffix}', n + 1
        target.write_bytes(data)
        try:
            audio.load(str(target))
        except Exception as e:  # not decodable: don't keep it
            target.unlink()
            raise ValueError(f'Could not read that audio file: {e}') from e
        vid = f'{w}/{target.name}'
        if label or voice:
            meta = self._meta()
            meta[vid] = {'label': label or target.stem, 'voice': voice}
            self._save_meta(meta)
        return next(v for v in self.variants()[w] if v.id == vid)

    def update(self, variant_id: str, label: str, voice: str) -> None:
        meta = self._meta()
        meta[variant_id] = {'label': label, 'voice': voice}
        self._save_meta(meta)


def rank(variants: list[Variant], voice: str, duration: float) -> list[Variant]:
    """Best first: clips tagged for this line's voice, then the closest length to the word being replaced."""
    def key(v: Variant):
        return (0 if v.voice and v.voice == voice else 1 if not v.voice else 2, abs(math.log(max(v.duration, 0.05) / max(duration, 0.05))))
    return sorted(variants, key=key)
