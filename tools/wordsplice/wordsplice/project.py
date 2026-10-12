"""Your choices, saved as you go in one JSON file so you can stop and carry on later."""
from __future__ import annotations

import json
import threading
from pathlib import Path


class Project:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.data = json.loads(path.read_text(encoding='utf8')) if path.exists() else {'lines': {}}
        self.data.setdefault('lines', {})
        self.data.setdefault('preferred', {})

    def _write(self) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, indent=1, ensure_ascii=False), encoding='utf8')
        tmp.replace(self.path)

    def line(self, rel: str) -> dict:
        return self.data['lines'].get(rel, {'edits': [], 'exported': False})

    def save_line(self, rel: str, edits: list[dict], exported: bool | None = None) -> None:
        with self._lock:
            cur = self.data['lines'].setdefault(rel, {'edits': [], 'exported': False})
            cur['edits'] = edits
            if exported is not None:
                cur['exported'] = exported
            elif cur.get('exported'):
                cur['exported'] = False  # changed since it was exported
            self._write()

    def prefer(self, word: str, voice: str, clip: str | None) -> None:
        """Remember which clip to use for `word` in lines of `voice` ('' = any voice)."""
        with self._lock:
            by_voice = self.data['preferred'].setdefault(word, {})
            if clip:
                by_voice[voice or '*'] = clip
            else:
                by_voice.pop(voice or '*', None)
            self._write()

    def preferred(self, word: str, voice: str) -> str | None:
        by_voice = self.data['preferred'].get(word, {})
        return by_voice.get(voice) or by_voice.get('*')
