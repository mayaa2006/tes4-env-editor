# Word Splicer

Replace single words inside existing voice lines (he → she, son → daughter, Martin → Ariella…) with clips you recorded or spliced yourself. You can keep several takes of the same word and choose between them for each line.

It runs on your computer only. Nothing is uploaded.

## The Windows program (easiest)

1. Download `WordSplicer-<version>-windows.zip` from the [latest release](https://github.com/mayaa2006/tes4-env-editor/releases/latest) and unzip it anywhere.
2. Double-click `WordSplicer.exe`. A small window asks for the **Voice lines folder** (the `splice` folder from the swap scan) and where to keep your work. Press **Start**.
3. The screen opens in your browser. Keep the small window open while you work; press **Stop** or close it when you're done.

Windows may say it "protected your PC" because the program isn't signed: choose **More info → Run anyway**. The first time you press *Find words in all lines* it downloads a speech model (about 140 MB), so it needs internet once. Your choices are remembered next time.

## Set up from source (Windows)

1. Install Python 3.10 or newer from <https://www.python.org/downloads/> and tick **Add python.exe to PATH**.
2. Open Command Prompt (not PowerShell) in this folder (`tools\wordsplice`) and run, giving the full path of the folder of voice lines you want to change:

   ```
   start.bat --lines "C:\path\to\swap\splice"
   ```

   The first run sets itself up (about 150 MB, a few minutes). After that your browser opens on the screen. Run `start.bat` with no options to get the same small window as the program.

The folder of lines is the `splice` folder the swap scan makes with `--extract`: it already holds the original audio for every line where someone else says "Martin", in the folder layout the game wants. Any folder of `.mp3`/`.wav` files works.

Your work is kept in the `wordsplice-work` folder inside `tools\wordsplice`: your clips, your choices, and the notes about where each word is. Finished lines go to `wordsplice-work\output`, in the same folder layout as the input.

## Using it

1. **Add clips** (right side). Type the word you recorded, give the take a name if you like, choose one or more audio files. Add as many takes of a word as you want. Tag a take with a voice (e.g. `breton/m`) and lines in that voice will pick it first.
2. Press **Find words in all lines** once. A small speech model listens to each line and notes where every word is spoken. It only does each line once.
3. Open a line. Words that get replaced by default are highlighted; click one to replace it (or click any other word to replace that too). For each replacement choose **Auto** or a particular take, press **▶ With replacements** to hear it, and nudge the edges by 10 ms if a cut sounds off. You can also drag the blue edges on the waveform, or drag over empty space to mark a part yourself.
4. Press **Save line as .mp3**. It is written at the original line's sample rate and bitrate.

**Auto-fill this line** and **Auto-fill every line** do steps 3–4 for every default word that has a clip in the bank. Words with no clip yet are listed so you know what to record next.

### Without the screen

```
python -m wordsplice auto --lines "C:\path\to\swap\splice"
```

Fills in and exports every line you haven't worked on in the screen, and lists the words you still have no clip for. Add `--redo` to include lines you already worked on.

## The word list

On the right, **Words to replace** holds pairs like `he = she`. The left word is found in the existing audio; the right word is the one you provide clips for. The defaults cover he/him/his/himself, son/boy/lad, emperor/prince/brother and Martin/Martin's. Contractions need their own clips (`he's = she's`, `he'll = she'll`). Edit the list and press **Save word list**.

`his` can mean `her` (his death → her death) or `hers` (it was his → it was hers). Change the word in the replacement box for the line where it matters.

## Where the clips live

```
wordsplice-work/bank/she/warm.wav
wordsplice-work/bank/she/flat.mp3
wordsplice-work/bank/ariella/take1.wav
```

You can drop files in by hand as well as using the screen.

## What it does to the audio

- Each cut moves to the quietest spot within 60 ms of where the word was found, so it doesn't click, and the clip is cross-faded in over 8 ms.
- A clip's silent lead-in and tail are trimmed, and it is levelled to match the word it replaces (up to ±12 dB).
- Length and pitch are not changed. If a take is much longer or shorter than the word, record another take; that is what the choice is for.

## Limits

- The words in the line come from a speech model, so an unusual name can be heard wrongly. Mark the part by hand if so.
- Mouth movement (`.lip` files) can't be made here. After splicing, regenerate them in the Construction Set.
- The replacement sounds like whoever recorded it. Different speakers will need different takes.

## Building the Windows program

`python build_exe.py <version>` (on Windows, after `pip install -r requirements.txt -r requirements-build.txt`) makes `dist\WordSplicer\WordSplicer.exe` and a zip of it. The "Word Splicer app" workflow does this on every pull request, runs the program's built-in self-check (`WordSplicer.exe --smoke report.txt`), and attaches the zip to the release when a new version reaches `main`.

## Checks

```
pip install -r requirements-dev.txt
playwright install chromium
python -m pytest
```
