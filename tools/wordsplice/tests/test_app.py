import json

import numpy as np
import pytest

from wordsplice import audio
from wordsplice.__main__ import main
from wordsplice.app import UserError

from .conftest import SR, wav_clip


def test_line_finds_default_words_and_snaps_edges(workspace):
    app, rel, _ = workspace
    d = app.line(rel)
    assert d['voice'] == 'breton/m' and d['text'] == 'Tell Martin, he is late.'
    targets = {w['norm']: w['replacement'] for w in d['words'] if w['target']}
    assert targets == {'martin': 'ariella', 'he': 'she'}
    assert all(a['end'] <= b['start'] + 1e-6 for a, b in zip(d['words'], d['words'][1:]))


def test_autofill_only_uses_words_that_have_clips(workspace):
    app, rel, _ = workspace
    app.bank.add('she', 'she.wav', wav_clip(550))
    edits, missing = app.auto_fill(rel)
    assert [e['word'] for e in edits] == ['he'] and missing == ['ariella']


def test_render_and_export_write_a_finished_mp3(workspace):
    app, rel, tmp = workspace
    app.bank.add('she', 'she.wav', wav_clip(550, 0.6))
    app.bank.add('ariella', 'ari.wav', wav_clip(450, 0.6))
    edits, _ = app.auto_fill(rel)
    assert len(edits) == 2
    res = app.export(rel, edits)
    out = audio.load(res['out'])
    assert out.sr == SR and out.duration == pytest.approx(res['duration'], abs=0.1)
    original = audio.load(str(app.lines_dir / rel))
    assert out.duration > original.duration  # both replacements are longer than the words they replace
    assert (app.out_dir / rel).exists() and app.project.line(rel)['exported'] is True


def test_missing_clip_is_a_friendly_error(workspace):
    app, rel, _ = workspace
    edits = [{'id': 'w1', 'start': 0.4, 'end': 0.7, 'replacement': 'ariella', 'clip': 'auto'}]
    with pytest.raises(UserError, match='no clip for "ariella"'):
        app.render(rel, edits)


def test_choosing_between_takes_and_remembering_a_favourite(workspace):
    app, rel, _ = workspace
    a = app.bank.add('she', 'one.wav', wav_clip(500, 0.3))
    b = app.bank.add('she', 'two.wav', wav_clip(900, 0.3))
    base = {'id': 'w2', 'start': 0.95, 'end': 1.25, 'replacement': 'she'}
    sa, _ = app.render(rel, [{**base, 'clip': a.id}])
    sb, _ = app.render(rel, [{**base, 'clip': b.id}])
    assert not np.allclose(sa[: len(sb)][: min(len(sa), len(sb))], sb[: min(len(sa), len(sb))])  # different takes -> different audio
    app.project.prefer('she', 'breton/m', b.id)
    assert app._resolve_clip({**base, 'clip': 'auto'}, 'breton/m') == b.id
    assert app._resolve_clip({**base, 'clip': a.id}, 'breton/m') == a.id  # an explicit pick still wins


def test_regions_can_be_marked_by_hand_and_must_not_overlap(workspace):
    app, rel, _ = workspace
    app.bank.add('she', 'she.wav', wav_clip(550))
    ok = [{'id': 'm1', 'start': 0.1, 'end': 0.3, 'replacement': 'she', 'clip': 'auto'}]
    app.render(rel, ok)
    with pytest.raises(UserError, match='overlap'):
        app.render(rel, ok + [{'id': 'm2', 'start': 0.25, 'end': 0.5, 'replacement': 'she', 'clip': 'auto'}])


def test_project_saves_and_reloads(workspace):
    app, rel, tmp = workspace
    app.project.save_line(rel, [{'id': 'w1', 'start': 0.4, 'end': 0.7, 'replacement': 'ariella'}])
    from wordsplice.project import Project
    assert Project(app.project.path).line(rel)['edits'][0]['replacement'] == 'ariella'
    assert app.state()['lines'][0]['edits'] == 1


def test_auto_command_writes_lines_and_reports_missing_words(workspace, capsys):
    app, rel, tmp = workspace
    app.bank.add('she', 'she.wav', wav_clip(550))
    main(['auto', '--lines', str(app.lines_dir), '--work', str(app.work_dir)])
    out = capsys.readouterr().out
    assert 'ariella: needed in 1 line' in out and (app.out_dir / rel).exists()


def test_rules_can_be_changed(workspace):
    app, rel, _ = workspace
    app.set_rules({'Late': 'early'})
    assert app.rules == {'late': 'early'}
    assert {w['norm'] for w in app.line(rel)['words'] if w['target']} == {'late'}
    assert json.loads((app.work_dir / 'rules.json').read_text()) == {'late': 'early'}


def test_state_includes_the_words_heard_so_lines_can_be_searched(workspace):
    app, rel, _ = workspace
    assert app.state()['lines'][0]['text'] == 'Tell Martin, he is late.'
