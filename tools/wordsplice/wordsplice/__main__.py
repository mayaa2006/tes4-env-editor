"""python -m wordsplice --lines <folder of voice lines> [options]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .app import App, UserError
from .server import serve


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='wordsplice', description='Replace single words inside existing voice lines with clips you provide.')
    p.add_argument('command', nargs='?', choices=['serve', 'auto'], default='serve',
                   help='serve: open the screen (default). auto: fill in and export every line that has clips for its words, no screen.')
    p.add_argument('--lines', type=Path, default=None, help='folder of existing voice lines (e.g. the "splice" folder from the swap scan)')
    p.add_argument('--work', type=Path, default=Path('wordsplice-work'), help='where your bank, choices and cache are kept (default: ./wordsplice-work)')
    p.add_argument('--out', type=Path, default=None, help='where finished lines are written (default: <work>/output)')
    p.add_argument('--plan', type=Path, default=None, help='swap-plan.json from the swap scan (optional; shows expected wording)')
    p.add_argument('--model', default='base.en', help='speech model used to find words (default: base.en)')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--no-browser', action='store_true')
    p.add_argument('--redo', action='store_true', help='auto: also redo lines you already worked on')
    p.add_argument('--gui', action='store_true', help='open the small window for choosing folders (the default when --lines is not given)')
    p.add_argument('--smoke', type=Path, default=None, metavar='REPORT', help=argparse.SUPPRESS)
    p.add_argument('--version', action='version', version=__version__)
    args = p.parse_args(argv)
    if args.smoke:
        from .smoke import run as smoke
        return smoke(args.smoke)
    if args.gui or (args.lines is None and args.command == 'serve'):
        from .launcher import run as gui
        gui()
        return 0
    if args.lines is None or not args.lines.is_dir():
        print(f'error: {args.lines} is not a folder' if args.lines else 'error: --lines <folder> is required', file=sys.stderr)
        return 2
    app = App(args.lines, args.work, args.out, args.plan, args.model)
    if args.command == 'auto':
        return run_auto(app, args.redo)
    serve(app, args.port, not args.no_browser)
    return 0


def run_auto(app: App, redo: bool) -> int:
    from . import lines

    done = skipped = 0
    missing_all: dict[str, int] = {}
    for rel in lines.scan(app.lines_dir):
        if app.project.line(rel)['edits'] and not redo:
            skipped += 1
            continue
        try:
            edits, missing = app.auto_fill(rel)
            for m in missing:
                missing_all[m] = missing_all.get(m, 0) + 1
            if not edits:
                print(f'  nothing to change: {rel}')
                continue
            app.export(rel, edits)
            done += 1
            print(f'  wrote {rel} ({len(edits)} word(s))')
        except UserError as e:
            print(f'  skipped {rel}: {e}')
    print(f'\nDone: {done} line(s) written to {app.out_dir}; {skipped} already worked on (use --redo to include).')
    if missing_all:
        print('Words with no clip in the bank yet (add some, then run again):')
        for w, n in sorted(missing_all.items(), key=lambda kv: -kv[1]):
            print(f'  {w}: needed in {n} line(s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
