import socket

import pytest

from wordsplice import settings
from wordsplice.align import AlignUnavailable, Aligner
from wordsplice.server import create_server, url_of

from .conftest import wav_clip


def test_settings_round_trip_and_defaults(tmp_path):
    f = tmp_path / 'cfg' / 'settings.json'
    assert settings.load(f).lines == '' and settings.load(f).work.endswith('WordSplicer')
    settings.save(settings.Settings(lines='C:/lines', plan='', work='C:/work'), f)
    s = settings.load(f)
    assert (s.lines, s.work) == ('C:/lines', 'C:/work')
    f.write_text('not json')
    assert settings.load(f).lines == ''  # a damaged file is ignored, not fatal


def test_checks_say_what_to_fix(tmp_path):
    assert 'Choose the folder' in settings.check(settings.Settings())
    assert 'does not exist' in settings.check(settings.Settings(lines=str(tmp_path / 'nope')))
    assert 'no audio files' in settings.check(settings.Settings(lines=str(tmp_path)))
    (tmp_path / 'a.wav').write_bytes(wav_clip(500))
    assert settings.check(settings.Settings(lines=str(tmp_path))) == ''
    assert 'swap plan' in settings.check(settings.Settings(lines=str(tmp_path), plan=str(tmp_path / 'missing.json')))


def test_server_falls_back_to_another_port_when_busy(workspace):
    app, _rel, _ = workspace
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        s.listen()
        busy = s.getsockname()[1]
        server = create_server(app, busy)
        try:
            assert server.server_address[1] != busy and url_of(server).startswith('http://127.0.0.1:')
        finally:
            server.server_close()


def test_finding_words_reports_a_missing_speech_model_on_screen(workspace, monkeypatch):
    app, _rel, _ = workspace
    # Make every line count as not yet listened to, and the speech library missing.
    monkeypatch.setattr(Aligner, 'cached', lambda self, path: False)
    monkeypatch.setattr(Aligner, 'ensure_model', lambda self: (_ for _ in ()).throw(AlignUnavailable('Automatic word finding needs faster-whisper')))
    app.align_all()
    import time
    for _ in range(50):
        if not app.progress['running']:
            break
        time.sleep(0.05)
    assert not app.progress['running'] and 'faster-whisper' in app.progress['error'] and app.progress['note'] == ''
