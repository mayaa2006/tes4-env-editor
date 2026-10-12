"""A quick self-check of a built program: can it start, serve the page and open a window? Used by the build, not by people."""
from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np


def run(report: Path | None) -> int:
    lines: list[str] = []
    ok = True

    def step(name: str, fn):
        nonlocal ok
        try:
            detail = fn()
            lines.append(f'ok   {name}{": " + str(detail) if detail else ""}')
        except Exception as e:
            ok = False
            lines.append(f'FAIL {name}: {type(e).__name__}: {e}')

    def serve_a_line():
        from . import audio
        from .app import App
        from .server import create_server, url_of
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'lines').mkdir()
            t = np.arange(22050) / 22050
            (d / 'lines' / 'x.mp3').write_bytes(audio.encode_mp3((0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32), 22050, 64))
            app = App(d / 'lines', d / 'work')
            # Pretend the line was already listened to, so the check never needs the speech model or the internet.
            app.aligner._cache_file(str(d / 'lines' / 'x.mp3')).write_text(json.dumps({'model': 'base.en', 'words': [{'text': 'hello', 'start': 0.1, 'end': 0.4}]}))
            server = create_server(app, 0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                req = urllib.request.Request(url_of(server) + 'api/state', headers={'X-Wordsplice': '1'})
                state = json.loads(urllib.request.urlopen(req, timeout=10).read())
                page = urllib.request.urlopen(urllib.request.Request(url_of(server)), timeout=10).read()
                assert len(state['lines']) == 1 and b'Word Splicer' in page
                line = json.loads(urllib.request.urlopen(urllib.request.Request(url_of(server) + 'api/line?path=x.mp3', headers={'X-Wordsplice': '1'}), timeout=10).read())
                assert len(line['peaks']) == 1600 and line['words'][0]['norm'] == 'hello'
            finally:
                server.shutdown()
                server.server_close()
        return 'page, state and a decoded line'

    def window():
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        from .launcher import Launcher
        Launcher(root)
        root.update()
        root.destroy()
        return 'launcher window created'

    def speech_libraries():
        frozen = getattr(sys, 'frozen', False)
        try:
            import ctranslate2
            import faster_whisper  # noqa: F401
            return f'ctranslate2 {ctranslate2.__version__}, cpu types {sorted(ctranslate2.get_supported_compute_types("cpu"))[:3]}'
        except ImportError as e:
            if frozen:
                raise
            return f'not installed here ({e})'

    def portable_folder():
        from . import paths
        d = paths.data_dir()
        if getattr(sys, 'frozen', False):
            assert d is not None and d.parent == paths.app_dir(), f'expected a data folder next to the program, got {d}'
        return str(d) if d else 'none (running from source)'

    step('portable data folder', portable_folder)
    step('serve a line', serve_a_line)
    step('open the window', window)
    step('speech libraries', speech_libraries)
    text = '\n'.join(lines) + ('\nSMOKE OK\n' if ok else '\nSMOKE FAILED\n')
    if report:
        report.write_text(text, encoding='utf8')
    if sys.stdout:
        print(text)
    return 0 if ok else 1
