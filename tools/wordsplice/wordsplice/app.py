"""The program's logic, independent of the web page."""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from . import audio, lines
from .align import Aligner, AlignUnavailable, snapped_words
from .bank import Bank, rank
from .project import Project
from .rules import load_rules, norm, save_rules, valid_word
from .splice import Edit, apply_edits, prepare


class UserError(ValueError):
    """Something the user can fix; the message is shown on screen."""


class App:
    def __init__(self, lines_dir: Path, work_dir: Path, out_dir: Path | None = None, plan: Path | None = None, model: str = 'base.en'):
        self.lines_dir = lines_dir.resolve()
        self.work_dir = work_dir.resolve()
        self.out_dir = (out_dir or self.work_dir / 'output').resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.bank = Bank(self.work_dir / 'bank')
        self.project = Project(self.work_dir / 'wordsplice-project.json')
        self.aligner = Aligner(self.work_dir / 'cache', model)
        self.rules_path = self.work_dir / 'rules.json'
        self.rules = load_rules(self.rules_path)
        self.plan = lines.load_plan(plan)
        self.progress = {'running': False, 'done': 0, 'total': 0, 'error': '', 'note': ''}

    # ---- lines ----
    def file_path(self, rel: str) -> Path:
        p = (self.lines_dir / rel).resolve()
        if self.lines_dir not in p.parents or not p.is_file():
            raise UserError(f'No line "{rel}" in {self.lines_dir}')
        return p

    def _hint(self, rel: str) -> str:
        return self.plan.get(Path(rel).stem.lower(), {}).get('original', '')

    def state(self) -> dict:
        out_lines = []
        for rel in lines.scan(self.lines_dir):
            saved = self.project.line(rel)
            words = self.aligner.cached_words(str(self.lines_dir / rel))
            out_lines.append({
                'path': rel, 'voice': lines.voice_of(rel),
                'aligned': words is not None,
                'targets': len([w for w in words or [] if norm(w['text']) in self.rules]),
                'text': ' '.join(w['text'] for w in words or []),
                'edits': len([e for e in saved['edits'] if not e.get('skip')]), 'exported': saved.get('exported', False),
                'subtitle': self.plan.get(Path(rel).stem.lower(), {}).get('subtitle', ''),
            })
        return {
            'lines': out_lines,
            'bank': {w: [v.__dict__ for v in vs] for w, vs in self.bank.variants().items()},
            'rules': self.rules, 'progress': self.progress, 'alignAvailable': self.aligner.available(),
            'linesDir': str(self.lines_dir), 'outDir': str(self.out_dir),
        }

    def line(self, rel: str) -> dict:
        path = self.file_path(rel)
        a = audio.load(str(path))
        message = ''
        try:
            words = snapped_words(self.aligner.words(str(path), a, self._hint(rel)), a)
        except AlignUnavailable as e:
            words, message = [], str(e)
        for w in words:
            w['replacement'] = self.rules.get(w['norm'], '')
            w['target'] = bool(w['replacement'])
        return {
            'path': rel, 'voice': lines.voice_of(rel), 'sr': a.sr, 'duration': round(a.duration, 3),
            'text': ' '.join(w['text'] for w in words), 'words': words, 'message': message,
            'saved': self.project.line(rel), 'peaks': audio.peaks(a.samples, 1600),
            'subtitle': self.plan.get(Path(rel).stem.lower(), {}).get('subtitle', ''),
        }

    # ---- rendering ----
    def _resolve_clip(self, edit: dict, voice: str) -> str:
        word = norm(edit.get('replacement', ''))
        options = self.bank.variants().get(word, [])
        if not options:
            raise UserError(f'There is no clip for "{word or "?"}" in the bank yet. Add one on the right.')
        if edit.get('clip') and edit['clip'] != 'auto':
            if not any(v.id == edit['clip'] for v in options):
                raise UserError(f'The clip "{edit["clip"]}" is no longer in the bank')
            return edit['clip']
        favourite = self.project.preferred(word, voice)
        if favourite and any(v.id == favourite for v in options):
            return favourite
        return rank(options, voice, max(0.05, float(edit['end']) - float(edit['start'])))[0].id

    def render(self, rel: str, edits: list[dict]) -> tuple[np.ndarray, int]:
        a = audio.load(str(self.file_path(rel)))
        voice = lines.voice_of(rel)
        todo = []
        for e in edits:
            if e.get('skip'):
                continue
            s, t = int(round(float(e['start']) * a.sr)), int(round(float(e['end']) * a.sr))
            if not 0 <= s < t <= len(a.samples):
                raise UserError('A word region is outside the line')
            clip = self.bank.get(self._resolve_clip(e, voice), a.sr).samples
            todo.append(Edit(s, t, prepare(clip, a.samples[s:t], a.sr)))
        if not todo:
            return a.samples, a.sr
        try:
            return apply_edits(a.samples, todo, a.sr), a.sr
        except ValueError as e:
            raise UserError(str(e)) from e

    def export(self, rel: str, edits: list[dict]) -> dict:
        samples, sr = self.render(rel, edits)
        path = self.file_path(rel)
        data = audio.encode_mp3(samples, sr, audio.guess_bitrate(str(path), audio.file_info(str(path)).duration))
        target = (self.out_dir / rel).with_suffix('.mp3')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.project.save_line(rel, edits, exported=True)
        return {'out': str(target), 'bytes': len(data), 'duration': round(len(samples) / sr, 3)}

    # ---- bank, rules, alignment ----
    def set_rules(self, rules: dict[str, str]) -> None:
        clean = {norm(k): norm(v) for k, v in rules.items() if norm(k) and valid_word(norm(v))}
        self.rules = clean
        save_rules(self.rules_path, clean)

    def rank(self, word: str, voice: str, duration: float) -> list[str]:
        return [v.id for v in rank(self.bank.variants().get(norm(word), []), voice, duration)]

    def auto_fill(self, rel: str) -> tuple[list[dict], list[str]]:
        """Edits for every default word in the line that has a clip in the bank, and the words that don't."""
        data = self.line(rel)
        have = self.bank.variants()
        edits, missing = [], []
        for w in data['words']:
            if not w['target']:
                continue
            if have.get(w['replacement']):
                edits.append({'id': f"w{w['i']}", 'start': w['start'], 'end': w['end'], 'word': w['norm'], 'replacement': w['replacement'], 'clip': 'auto', 'text': w['text']})
            elif w['replacement'] not in missing:
                missing.append(w['replacement'])
        return edits, missing

    def align_all(self) -> None:
        if self.progress['running']:
            return
        rels = lines.scan(self.lines_dir)
        self.progress.update(running=True, done=0, total=len(rels), error='', note='')

        def work():
            try:
                if any(not self.aligner.cached(str(self.lines_dir / r)) for r in rels):
                    self.progress['note'] = 'Loading the speech model. The first time this downloads about 140 MB, so it can take a few minutes.'
                    self.aligner.ensure_model()
                    self.progress['note'] = ''
                for rel in rels:
                    path = self.lines_dir / rel
                    if not self.aligner.cached(str(path)):
                        self.aligner.words(str(path), audio.load(str(path)), self._hint(rel))
                    self.progress['done'] += 1
            except Exception as e:  # shown on screen, not raised in the thread
                self.progress['error'] = str(e)
                self.progress['note'] = ''
            finally:
                self.progress['running'] = False

        threading.Thread(target=work, daemon=True).start()
