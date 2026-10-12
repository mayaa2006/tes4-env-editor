# TES4 Env Editor

An editor for Oblivion (TES4) `.esm`/`.esp` plugins, with automated character-swap tooling: find every place a character's name appears, list the voice files and subtitles that go with them, and replace them in bulk.

> **Status: just started.** This repository was seeded from [tes5-env-editor](https://github.com/mayaa2006/tes5-env-editor), the Skyrim editor, and still contains only that code. Oblivion support does not exist yet. See [ROADMAP.md](ROADMAP.md).

## First goal

Replace Martin Septim with Ariella Septim (female) in `Oblivion.esm`:

1. Scan for Martin's NPC record, his dialogue lines, quest and book text, scripts and conditions that name him.
2. List his voice files with the subtitle for each.
3. Preview and apply the name, subtitle and pronoun changes in bulk, with undo.
4. Produce a numbered recording script with the exact filenames, so you only have to drop in audio.

Lip-sync (`.lip`) files can only be generated with the original Construction Set; the tool will list which ones need it.

## Skyrim code

The packages and app inherited from the Skyrim editor are documented in [ARCHITECTURE.md](ARCHITECTURE.md). Oblivion's record and group headers are 20 bytes (Skyrim's are 24), so it needs its own plugin reader.
