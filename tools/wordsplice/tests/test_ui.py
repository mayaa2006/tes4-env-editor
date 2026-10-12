"""Drives the real page in a browser. Skipped when Playwright or a browser isn't installed."""
import glob
import os
import threading
from http.server import ThreadingHTTPServer

import pytest

from wordsplice import audio
from wordsplice.server import make_handler

from .conftest import wav_clip

sync_api = pytest.importorskip('playwright.sync_api')


def find_chromium():
    for pattern in (os.environ.get('CHROMIUM_PATH', ''), '/opt/pw-browsers/chromium', '/opt/pw-browsers/chromium-*/chrome-linux/chrome'):
        for p in glob.glob(pattern) if pattern else []:
            if os.path.isfile(p):
                return p
    return None


@pytest.fixture
def page(workspace):
    app, rel, tmp = workspace
    srv = ThreadingHTTPServer(('127.0.0.1', 0), None)
    port = srv.server_address[1]
    srv.RequestHandlerClass = make_handler(app, port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=find_chromium()) if find_chromium() else p.chromium.launch()
        except Exception as e:
            pytest.skip(f'No browser available: {e}')
        pg = browser.new_page(viewport={'width': 1280, 'height': 800})
        pg.goto(f'http://127.0.0.1:{port}/')
        pg.app, pg.rel = app, rel
        yield pg
        browser.close()
    srv.shutdown()


def no_sideways_scroll(pg):
    return pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


def test_first_run_help_then_add_clips_pick_a_take_and_save(page):
    pg, app, rel = page, page.app, page.rel
    pg.wait_for_selector('#help[open]')  # first run with no clips: the how-to opens by itself
    pg.click('#help button')
    assert 'No clips yet' in pg.inner_text('#bankEmpty')
    assert 'Pick a line' in pg.inner_text('#editorEmpty')

    pg.fill('#addWord', 'she')
    pg.set_input_files('#addFile', [
        {'name': 'warm.wav', 'mimeType': 'audio/wav', 'buffer': wav_clip(500, 0.4)},
        {'name': 'flat.wav', 'mimeType': 'audio/wav', 'buffer': wav_clip(800, 0.4)},
    ])
    pg.click('#addBtn')
    pg.wait_for_selector('text=2 takes')

    pg.click('#lines li')
    pg.wait_for_selector('#words .word')
    assert [w.inner_text() for w in pg.query_selector_all('#words .word.target')] == ['Martin,', 'he']
    pg.click('#words .word.target >> nth=1')  # the word "he"
    card = pg.wait_for_selector('.edit.sel')
    assert 'he' in card.inner_text() and card.query_selector('input[type=text]').input_value() == 'she'
    assert len(card.query_selector_all('.variant')) == 3  # Auto + the two takes
    pg.locator('.edit.sel .variant input').nth(1).click()  # the first take in the list (flat, as takes are listed A-Z) (the list redraws on choosing)
    pg.wait_for_selector('.edit.sel .variant.on:has-text("flat")')
    pg.click('#export')
    pg.wait_for_selector('#msg.ok')
    assert (app.out_dir / rel).exists()
    assert app.project.line(rel)['edits'][0]['clip'] == 'she/flat.wav'
    assert 'exported' in pg.inner_text('#lines li')
    assert no_sideways_scroll(pg)


def test_missing_clip_is_explained_and_undo_brings_edits_back(page):
    pg = page
    pg.click('#help button')
    pg.click('#lines li')
    pg.click('#words .word.target >> nth=0')  # "Martin,": there is no ariella clip yet
    assert 'No clip for' in pg.inner_text('.edit.sel .variants')
    pg.click('.edit.sel .rm')
    assert pg.query_selector('.edit') is None and 'Nothing is being replaced' in pg.inner_text('#noEdits')
    pg.click('#undo')
    assert pg.query_selector('.edit') is not None
    pg.click('#playResult')
    pg.wait_for_selector('#msg.err')  # rendering needs the clip, and says so
    assert 'no clip' in pg.inner_text('#msg')


def test_marking_a_word_by_hand_on_the_waveform(page):
    pg = page
    pg.click('#help button')
    pg.click('#lines li')
    box = pg.query_selector('#wave').bounding_box()
    pg.mouse.move(box['x'] + box['width'] * 0.1, box['y'] + 40)
    pg.mouse.down()
    pg.mouse.move(box['x'] + box['width'] * 0.25, box['y'] + 40)
    pg.mouse.up()
    assert 'marked part' in pg.inner_text('.edit.sel')
