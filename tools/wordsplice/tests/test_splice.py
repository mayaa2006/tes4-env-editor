import numpy as np
import pytest

from wordsplice.splice import Edit, apply_edits, crossfade_join, match_level, rms, snap, trim_silence

from .conftest import SR, gap, make_line, tone


def test_trim_silence_removes_quiet_edges_but_keeps_a_little():
    x = np.concatenate([gap(0.3), tone(400, 0.2), gap(0.3)])
    y = trim_silence(x, SR)
    assert 0.2 * SR <= len(y) <= 0.2 * SR + 0.02 * SR


def test_snap_moves_a_boundary_into_the_quiet_gap():
    x, timing = make_line([('a', 300), ('b', 500)], pause=0.2)
    end_of_a = timing[0]['end']
    s = snap(x, SR, end_of_a - 0.02)  # recogniser put the edge slightly inside the word
    assert end_of_a - 0.001 <= s / SR <= end_of_a + 0.2
    assert abs(x[s]) < 0.01


def test_match_level_scales_to_reference_and_never_clips():
    quiet, loud = tone(400, 0.2, 0.05), tone(400, 0.2, 0.4)
    assert rms(match_level(tone(400, 0.2, 0.2), loud)) == pytest.approx(rms(loud), rel=0.05)
    assert rms(match_level(quiet, loud)) == pytest.approx(rms(quiet) * 4, rel=0.05)  # boost is capped at 12 dB
    assert np.max(np.abs(match_level(tone(400, 0.2, 0.9), tone(400, 0.2, 0.95)))) <= 0.99


def test_crossfade_join_overlaps_by_n_samples():
    a, b = np.ones(1000, np.float32), np.ones(1000, np.float32)
    out = crossfade_join(a, b, 100)
    assert len(out) == 1900 and out[0] == 1 and out[-1] == 1
    assert 0.95 < out[950] < 1.45  # equal-power mix of two identical signals stays near unity


def test_apply_edits_replaces_the_range_and_changes_length():
    x, timing = make_line([('a', 300), ('b', 500), ('c', 700)])
    s, e = int(timing[1]['start'] * SR), int(timing[1]['end'] * SR)
    clip = tone(900, 0.5)
    out = apply_edits(x, [Edit(s, e, clip)], SR)
    assert len(out) == pytest.approx(len(x) - (e - s) + len(clip), abs=3 * SR * 0.008)
    # The start of the line is untouched
    assert np.allclose(out[: s - int(SR * 0.02)], x[: s - int(SR * 0.02)])


def test_apply_edits_rejects_overlaps():
    x = np.zeros(SR, np.float32)
    with pytest.raises(ValueError):
        apply_edits(x, [Edit(100, 400, x[:50]), Edit(300, 500, x[:50])], SR)
