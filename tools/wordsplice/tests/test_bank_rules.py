import pytest

from wordsplice.bank import Bank, rank
from wordsplice.rules import DEFAULT_RULES, norm, valid_word

from .conftest import wav_clip


def test_norm_strips_punctuation_and_curly_apostrophes():
    assert norm('Martin,') == 'martin'
    assert norm('Martin’s') == "martin's"
    assert norm('"He\'ll"') == "he'll"
    assert norm('...') == ''


def test_default_rules_cover_the_basics():
    for a, b in {'he': 'she', 'son': 'daughter', 'emperor': 'empress', 'martin': 'ariella', "martin's": "ariella's"}.items():
        assert DEFAULT_RULES[a] == b


def test_valid_word():
    assert valid_word("she's") and valid_word('half-elf') and not valid_word('two words') and not valid_word('../x')


def test_bank_add_list_and_rank(tmp_path):
    bank = Bank(tmp_path / 'bank')
    bank.add('She', 'flat.wav', wav_clip(500, 0.3))
    bank.add('she', 'long take.wav', wav_clip(500, 0.9), label='slow', voice='breton/m')
    vs = bank.variants()['she']
    assert [v.file for v in vs] == ['flat.wav', 'long take.wav']
    assert vs[1].label == 'slow' and vs[1].voice == 'breton/m'
    # The clip tagged for this voice wins, even though the other is closer in length
    assert rank(vs, 'breton/m', 0.3)[0].file == 'long take.wav'
    assert rank(vs, 'nord/f', 0.3)[0].file == 'flat.wav'


def test_bank_never_overwrites_and_rejects_bad_input(tmp_path):
    bank = Bank(tmp_path / 'bank')
    a = bank.add('she', 'x.wav', wav_clip(500))
    b = bank.add('she', 'x.wav', wav_clip(600))
    assert a.id != b.id and len(bank.variants()['she']) == 2
    with pytest.raises(ValueError):
        bank.add('two words', 'x.wav', wav_clip(500))
    with pytest.raises(ValueError):
        bank.add('she', 'x.txt', b'hello')
    with pytest.raises(ValueError):
        bank.add('she', 'broken.wav', b'not audio')
    assert len(bank.variants()['she']) == 2  # the broken file was not kept
    with pytest.raises(FileNotFoundError):
        bank.get('../outside.wav')
