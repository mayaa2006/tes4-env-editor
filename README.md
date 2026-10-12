# TES4 Env Editor

An editor for Oblivion (TES4) `.esm`/`.esp` plugins, with automated character-swap tooling: find every place a character's name appears, list the voice files and subtitles that go with them, and replace them in bulk.

> **Status: early.** The Oblivion plugin reader and the character-swap scan/build work on the real `Oblivion.esm` (read back byte for byte). The rest of this repository is still the Skyrim editor it was copied from. Voice-archive (BSA) checks are not done yet. See [ROADMAP.md](ROADMAP.md).

## First goal

Replace Martin Septim with Ariella Septim (female) in `Oblivion.esm`:

1. Scan for Martin's NPC record, his dialogue lines, quest and book text, scripts and conditions that name him.
2. List his voice files with the subtitle for each.
3. Preview and apply the name, subtitle and pronoun changes in bulk, with undo.
4. Produce a numbered recording script with the exact filenames, so you only have to drop in audio.

### Try it

Needs Node 22+ and `npm ci`.

```
npm run tes4 -- swap-scan  "<path>/Oblivion.esm" --out swap
npm run tes4 -- swap-build "<path>/Oblivion.esm" swap/swap-plan.json --out ArielleSwap.esp [--accept-suggestions]
```

`swap-scan` writes into the folder: `summary.md` (what needs doing), `recording-script.csv` (one row per audio file: the exact file name, where to save it, the new subtitle, and whether to record the whole line or splice the name into the existing audio), `pronoun-check.csv` and `swap-plan.json`. Edit any `proposed` subtitle in `swap-plan.json` before building. `swap-build` writes a small override `.esp` (needs `Oblivion.esm`); the game file is never changed. Gendered words (he, him, son...) are only rewritten with `--accept-suggestions`, because they can also refer to other characters; check the result.

On the real game file the scan finds 421 spoken responses by Martin, 107 where others say his name, and 182 subtitles/texts to change. "Martina Floria" is left alone.

Lip-sync (`.lip`) files can only be generated with the original Construction Set; the tool will list which ones need it.

## Skyrim code

The packages and app inherited from the Skyrim editor are documented in [ARCHITECTURE.md](ARCHITECTURE.md). Oblivion's record and group headers are 20 bytes (Skyrim's are 24), so it needs its own plugin reader.
