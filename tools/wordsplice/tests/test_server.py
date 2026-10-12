import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from wordsplice.server import make_handler

from .conftest import wav_clip


@pytest.fixture
def server(workspace):
    app, rel, _ = workspace
    srv = ThreadingHTTPServer(('127.0.0.1', 0), None)
    port = srv.server_address[1]
    srv.RequestHandlerClass = make_handler(app, port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield app, rel, port
    srv.shutdown()


def call(port, path, data=None, headers=None, host=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, headers={'X-Wordsplice': '1', **(headers or {})})
    if host:
        req.add_unredirected_header('Host', host)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_page_state_and_line(server):
    app, rel, port = server
    assert call(port, '/')[0] == 200
    state = json.loads(call(port, '/api/state')[1])
    assert state['lines'][0]['path'] == rel and state['lines'][0]['targets'] == 2
    line = json.loads(call(port, '/api/line?path=' + rel)[1])
    assert line['words'][1]['target'] and len(line['peaks']) == 1600


def test_other_websites_and_odd_paths_are_refused(server):
    app, rel, port = server
    assert call(port, '/api/state', host='evil.example')[0] == 403
    assert call(port, '/api/save', b'{}', headers={'X-Wordsplice': ''})[0] == 403
    code, body = call(port, '/api/audio?path=../../etc/passwd')
    assert code == 400 and b'No line' in body
    assert call(port, '/api/clip?id=../../x')[0] == 404


def test_add_clip_render_and_export_over_http(server):
    app, rel, port = server
    code, _ = call(port, '/api/bank/add?word=she&filename=she.wav&label=warm', wav_clip(500, 0.5))
    assert code == 200
    edits = [{'id': 'w2', 'start': 0.95, 'end': 1.25, 'replacement': 'she', 'clip': 'auto'}]
    code, wav = call(port, '/api/render', json.dumps({'path': rel, 'edits': edits}).encode())
    assert code == 200 and wav[:4] == b'RIFF'
    code, body = call(port, '/api/export', json.dumps({'path': rel, 'edits': edits}).encode())
    assert code == 200 and (app.out_dir / rel).exists()
    code, body = call(port, '/api/render', json.dumps({'path': rel, 'edits': [{**edits[0], 'replacement': 'nothing'}]}).encode())
    assert code == 400 and b'no clip' in body
