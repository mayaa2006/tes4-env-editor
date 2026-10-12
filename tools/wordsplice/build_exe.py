"""Build the Windows program: python build_exe.py [version]

Makes dist/WordSplicer/WordSplicer.exe (a folder, so it starts quickly) and dist/WordSplicer-<version>-windows.zip.
Run on Windows with:  pip install -r requirements.txt pyinstaller
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
# Packages with data files or native libraries that PyInstaller must copy whole.
COLLECT = ['cffi', 'faster_whisper', 'ctranslate2', 'tokenizers', 'onnxruntime', 'av', 'miniaudio', 'lameenc', 'certifi', 'huggingface_hub']


def main() -> int:
    version = sys.argv[1] if len(sys.argv) > 1 else '0.0.0'
    cmd = [
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--name', 'WordSplicer',
        '--add-data', f'wordsplice{os.sep}static{os.pathsep}wordsplice{os.sep}static',
        '--hidden-import', '_cffi_backend',  # the audio decoder (miniaudio) is a cffi module
    ]
    for pkg in COLLECT:
        if importlib.util.find_spec(pkg):
            cmd += ['--collect-all', pkg]
        else:
            print(f'note: {pkg} is not installed, so it is not included')
    cmd.append('launcher_main.py')
    subprocess.run(cmd, cwd=HERE, check=True)
    out = HERE / 'dist' / 'WordSplicer'
    if not (out / 'WordSplicer.exe').exists() and not (out / 'WordSplicer').exists():
        print('error: the program was not built', file=sys.stderr)
        return 1
    (out / 'README.txt').write_text(
        'Word Splicer\n\nDouble-click WordSplicer.exe. Choose the folder of voice lines, then press Start.\n'
        'The first time you press "Find words in all lines", it downloads a speech model (about 140 MB), so it needs internet once.\n'
        'Windows may say it "protected your PC" because the program is not signed: choose More info, then Run anyway.\n', encoding='utf8')
    archive = shutil.make_archive(str(HERE / 'dist' / f'WordSplicer-{version}-windows'), 'zip', HERE / 'dist', 'WordSplicer')
    print(f'built {archive}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
