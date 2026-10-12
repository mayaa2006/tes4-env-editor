"""Where the program keeps its files.

The Windows program is portable: everything it writes (settings, your clips, your work, the speech
model) goes in a `data` folder next to WordSplicer.exe. Copy or move that folder and everything comes
with it; delete it and nothing is left behind. Run from source it keeps the old places unless
WORDSPLICER_DATA names a folder.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path | None:
    """The folder holding WordSplicer.exe, or None when running from source."""
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else None


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / '.write-test'
        probe.write_text('x')
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path | None:
    """The portable data folder, or None if there isn't one (source runs, or a read-only install folder)."""
    env = os.environ.get('WORDSPLICER_DATA')
    if env:
        return Path(env).resolve() if _writable(Path(env)) else None
    base = app_dir()
    if base and _writable(base / 'data'):
        return base / 'data'
    return None


def models_dir() -> Path | None:
    d = data_dir()
    return d / 'models' if d else None


def use_portable_environment() -> None:
    """Point the model downloader at the data folder, so nothing is written under the user's profile."""
    m = models_dir()
    if m:
        m.mkdir(parents=True, exist_ok=True)
        os.environ['HF_HOME'] = str(m)
        os.environ['HF_HUB_CACHE'] = str(m)
