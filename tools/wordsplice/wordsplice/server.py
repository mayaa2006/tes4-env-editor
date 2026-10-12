"""A small web server on this computer only. The page talks to it; nothing leaves your machine."""
from __future__ import annotations

import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import audio
from .app import App, UserError

STATIC = Path(__file__).parent / 'static'


def make_handler(app: App, port: int):
    allowed_hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep the console quiet
            pass

        def _send(self, data: bytes, ctype: str, status: int = 200):
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, status: int = 200):
            self._send(json.dumps(obj, ensure_ascii=False).encode('utf8'), 'application/json; charset=utf-8', status)

        def _body(self) -> bytes:
            return self.rfile.read(int(self.headers.get('Content-Length') or 0))

        def _guard(self, post: bool) -> bool:
            # Only this computer's own page may talk to the server (stops other websites from poking it).
            if self.headers.get('Host', '') not in allowed_hosts:
                self._json({'error': 'Wrong host'}, 403)
                return False
            if post and self.headers.get('X-Wordsplice') != '1':
                self._json({'error': 'Missing header'}, 403)
                return False
            return True

        def _handle(self, post: bool):
            if not self._guard(post):
                return
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                self._route(url.path, q, post)
            except UserError as e:
                self._json({'error': str(e)}, 400)
            except FileNotFoundError as e:
                self._json({'error': str(e)}, 404)
            except Exception as e:  # shown on screen
                traceback.print_exc()
                self._json({'error': f'{type(e).__name__}: {e}'}, 500)

        def do_GET(self):
            self._handle(False)

        def do_POST(self):
            self._handle(True)

        def _route(self, path: str, q: dict, post: bool):
            if not post:
                if path == '/':
                    return self._send((STATIC / 'index.html').read_bytes(), 'text/html; charset=utf-8')
                if path == '/api/state':
                    return self._json(app.state())
                if path == '/api/line':
                    return self._json(app.line(q['path']))
                if path == '/api/audio':
                    p = app.file_path(q['path'])
                    return self._send(p.read_bytes(), 'audio/mpeg' if p.suffix.lower() == '.mp3' else 'audio/wav')
                if path == '/api/clip':
                    c = (app.bank.root / q['id']).resolve()
                    if app.bank.root.resolve() not in c.parents or not c.is_file():
                        raise FileNotFoundError(q['id'])
                    return self._send(c.read_bytes(), 'audio/mpeg' if c.suffix.lower() == '.mp3' else 'audio/wav')
                if path == '/api/rank':
                    return self._json({'ids': app.rank(q['word'], q.get('voice', ''), float(q.get('duration', 0.3)))})
                if path == '/api/autofill':
                    edits, missing = app.auto_fill(q['path'])
                    return self._json({'edits': edits, 'missing': missing})
                return self._send(b'Not found', 'text/plain', 404)
            body = self._body()
            if path == '/api/bank/add':
                v = app.bank.add(q['word'], q['filename'], body, q.get('label', ''), q.get('voice', ''))
                return self._json(v.__dict__)
            data = json.loads(body or b'{}')
            if path == '/api/render':
                samples, sr = app.render(data['path'], data['edits'])
                return self._send(audio.to_wav_bytes(samples, sr), 'audio/wav')
            if path == '/api/export':
                return self._json(app.export(data['path'], data['edits']))
            if path == '/api/save':
                app.project.save_line(data['path'], data['edits'])
                return self._json({'ok': True})
            if path == '/api/bank/update':
                app.bank.update(data['id'], data.get('label', ''), data.get('voice', ''))
                return self._json({'ok': True})
            if path == '/api/prefer':
                app.project.prefer(data['word'], data.get('voice', ''), data.get('clip'))
                return self._json({'ok': True})
            if path == '/api/rules':
                app.set_rules(data['rules'])
                return self._json({'rules': app.rules})
            if path == '/api/align-all':
                app.align_all()
                return self._json(app.progress)
            return self._send(b'Not found', 'text/plain', 404)

    return Handler


def serve(app: App, port: int = 8765, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(app, port))
    url = f'http://127.0.0.1:{port}/'
    print(f'Word Splicer is running at {url}  (close this window or press Ctrl+C to stop)')
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
