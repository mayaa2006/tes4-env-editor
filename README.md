# TES4 Env Editor

An editor for Oblivion (TES4) `.esm`/`.esp` plugins, with automated character-swap tooling: find every place a character's name appears, list the voice files and subtitles that go with them, and replace them in bulk.

> **Status: early.** The Oblivion plugin reader and the character-swap scan/build work on the real `Oblivion.esm` (read back byte for byte). The rest of this repository is still the Skyrim editor it was copied from. The voice archives are checked: file names match the real game audio. See [ROADMAP.md](ROADMAP.md).

## First goal

Replace Martin Septim with Ariella Septim (female) in `Oblivion.esm`:

1. Scan for Martin's NPC record, his dialogue lines, quest and book text, scripts and conditions that name him.
2. List his voice files with the subtitle for each.
3. Preview and apply the name, subtitle and pronoun changes in bulk, with undo.
4. Produce a numbered recording script with the exact filenames, so you only have to drop in audio.

### Try it

Needs Node 22+ and `npm ci`.

```
npm run tes4 -- swap-scan  "<path>/Oblivion.esm" --out swap --extract
npm run tes4 -- swap-build "<path>/Oblivion.esm" swap/swap-plan.json --out ArielleSwap.esp [--accept-suggestions]
```

`swap-scan` also looks for `Oblivion - Voices1.bsa` / `Voices2.bsa` next to the `.esm` (or give `--voice <bsa>`), checks each audio file exists, and with `--extract` copies the originals out: `splice/` holds the files where someone else says the name (edit them in place; keep the folder layout), `reference/` holds Martin's own originals for timing. It writes into the folder: `summary.md` (what needs doing), `recording-script.csv` (one row per audio file: the exact file name, where to save it, the new subtitle, and whether to record the whole line or splice the name into the existing audio), `pronoun-check.csv` and `swap-plan.json`. Edit any `proposed` subtitle in `swap-plan.json` before building. `swap-build` writes a small override `.esp` (needs `Oblivion.esm`); the game file is never changed. Gendered words (he, him, son...) are only rewritten with `--accept-suggestions`, because they can also refer to other characters; check the result.

On the real game files the scan finds 421 spoken responses by Martin (420 have original audio; one is text-only), 107 where others say his name (all have audio to splice), and 182 subtitles/texts to change. Martin's audio is all in `Imperial\M`; the new lines go in `Imperial\F`. "Martina Floria" is left alone.

### Replace words in existing audio

`tools/wordsplice` is a small program for the splice work: give it clips of words you recorded (she, daughter, Ariella…, several takes of each if you like) and it replaces he/son/Martin… inside the existing lines, with a picture of each line, per-word choice of take, undo, and automatic find-and-replace across all lines. See [tools/wordsplice/README.md](tools/wordsplice/README.md).

Lip-sync (`.lip`) files can only be generated with the original Construction Set; the tool will list which ones need it.

## Skyrim code

The packages and app inherited from the Skyrim editor are documented in [ARCHITECTURE.md](ARCHITECTURE.md). Oblivion's record and group headers are 20 bytes (Skyrim's are 24), so it needs its own plugin reader.
