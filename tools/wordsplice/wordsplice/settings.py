"""What the launcher window remembers between runs, and the checks it does before starting."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from . import audio, paths


def settings_dir() -> Path:
    portable = paths.data_dir()
    if portable:
        return portable
    base = os.environ.get('APPDATA') or os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(base) / 'WordSplicer'


def default_work_dir() -> str:
    portable = paths.data_dir()
    return str(portable / 'work') if portable else str(Path.home() / 'Documents' / 'WordSplicer')


def _relative_to_data(value: str) -> str:
    """In portable mode, keep paths inside the data folder relative, so the folder still works after it is moved."""
    portable = paths.data_dir()
    if portable and value:
        try:
            return Path(value).resolve().relative_to(portable).as_posix()
        except ValueError:
            pass
    return value


def _absolute(value: str) -> str:
    portable = paths.data_dir()
    if portable and value and not Path(value).is_absolute() and not (len(value) > 1 and value[1] == ':'):
        return str(portable / value)
    return value


@dataclass
class Settings:
    lines: str = ''
    plan: str = ''
    work: str = ''

    def __post_init__(self):
        self.work = self.work or default_work_dir()


def load(path: Path | None = None) -> Settings:
    path = path or settings_dir() / 'settings.json'
    try:
        raw = json.loads(path.read_text(encoding='utf8'))
        return Settings(**{k: _absolute(str(raw.get(k, ''))) for k in ('lines', 'plan', 'work')})
    except (OSError, ValueError):
        return Settings()


def save(s: Settings, path: Path | None = None) -> None:
    path = path or settings_dir() / 'settings.json'
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({k: _relative_to_data(v) for k, v in asdict(s).items()}, indent=1), encoding='utf8')
    except OSError:
        pass  # not being able to remember is not worth stopping for


def check(s: Settings) -> str:
    """'' when the choices can be used, otherwise what to fix, in plain words."""
    if not s.lines.strip():
        return 'Choose the folder of voice lines first.'
    lines = Path(s.lines.strip())
    if not lines.is_dir():
        return f'That folder of voice lines does not exist: {lines}'
    if not any(p.suffix.lower() in audio.AUDIO_EXTENSIONS for p in lines.rglob('*')):
        return 'There are no audio files (.mp3, .wav, .flac, .ogg) in that folder. Choose the folder that holds the voice lines, e.g. the "splice" folder.'
    if s.plan.strip() and not Path(s.plan.strip()).is_file():
        return f'That swap plan file does not exist: {s.plan}'
    return ''
