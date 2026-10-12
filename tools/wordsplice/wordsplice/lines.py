"""The existing voice lines you want to change: any folder of audio files."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import audio


def voice_of(rel: str) -> str:
    """'sound/voice/oblivion.esm/breton/m/x.mp3' -> 'breton/m'; anything else -> ''."""
    m = re.search(r'/voice/[^/]+/([^/]+)/([mf])/[^/]+$', rel.lower())
    return f'{m.group(1)}/{m.group(2)}' if m else ''


def scan(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.suffix.lower() in audio.AUDIO_EXTENSIONS)


def load_plan(plan_path: Path | None) -> dict[str, dict]:
    """Optional swap-plan.json from the Oblivion swap scan: gives the expected wording for each file."""
    if not plan_path or not plan_path.exists():
        return {}
    plan = json.loads(plan_path.read_text(encoding='utf8'))
    out: dict[str, dict] = {}
    for v in plan.get('voice', []):
        name = (v.get('audioName') or v['file']).lower()
        out[name] = {'subtitle': v.get('subtitle', ''), 'original': v.get('originalSubtitle', '')}
    return out
