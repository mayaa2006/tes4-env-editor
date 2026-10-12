"""Which words get replaced by default, and how words are compared."""
from __future__ import annotations

import json
import re
from pathlib import Path

# Word on the left is found in the existing audio; the word on the right is what you provide a clip for.
DEFAULT_RULES: dict[str, str] = {
    'martin': 'ariella',
    "martin's": "ariella's",
    'he': 'she',
    "he's": "she's",
    "he'll": "she'll",
    "he'd": "she'd",
    'him': 'her',
    'his': 'her',
    'himself': 'herself',
    'son': 'daughter',
    'boy': 'girl',
    'lad': 'lass',
    'emperor': 'empress',
    'prince': 'princess',
    'brother': 'sister',
}


def norm(word: str) -> str:
    """Lower-case, straight apostrophes, no surrounding punctuation: 'Martin,' -> 'martin'."""
    w = word.strip().lower().replace('’', "'").replace('‘', "'")
    return re.sub(r"^[^a-z0-9']+|[^a-z0-9']+$", '', w).strip("'") if w else ''


def valid_word(word: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", word))


def load_rules(path: Path) -> dict[str, str]:
    if path.exists():
        raw = json.loads(path.read_text(encoding='utf8'))
        return {norm(k): norm(v) for k, v in raw.items() if norm(k) and norm(v)}
    return dict(DEFAULT_RULES)


def save_rules(path: Path, rules: dict[str, str]) -> None:
    path.write_text(json.dumps(dict(sorted(rules.items())), indent=2), encoding='utf8')
