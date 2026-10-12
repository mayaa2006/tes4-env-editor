"""Entry point of the Windows program (built with PyInstaller). Opens the launcher window."""
import os
import sys

# A windowed program has no console; make printing harmlessly do nothing instead of crashing.
for stream in ('stdout', 'stderr'):
    if getattr(sys, stream) is None:
        setattr(sys, stream, open(os.devnull, 'w'))
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')

from wordsplice.__main__ import main  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(main())
