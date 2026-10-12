# Changelog

Each version here is published as a Windows installer and portable exe on the [releases page](https://github.com/mayaa2006/tes4-env-editor/releases).

## 0.2.0

- **Oblivion plugin reader and writer.** Reads `Oblivion.esm` (20-byte headers, compressed records) and writes it back byte for byte.
- **Character swap, first version.** `npm run tes4 -- swap-scan` finds a character (Martin by default) and lists every spoken line with its audio file name, every line where someone else says the name, and every other text that carries the name. It writes a recording script, a summary and an editable plan. `swap-build` writes an override `.esp` with the new names, subtitles and the character made female. Gendered words are flagged and only rewritten when you accept the suggestions. It also reads the voice archives (`Oblivion - Voices*.bsa`), confirms each audio file exists, and with `--extract` copies the originals out for splicing. The Windows app itself does not have this yet.

## 0.1.0

- **Starting point.** This repository begins as a copy of the Skyrim editor (TES5 Env Editor). It does not read Oblivion plugins yet. Coming next: an Oblivion (TES4) plugin reader and a character-swap tool that finds a character's name, dialogue subtitles and voice files so they can be replaced (first goal: Martin Septim to Ariella Septim).
