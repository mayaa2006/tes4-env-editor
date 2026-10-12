# Changelog

Each version here is published as a Windows installer and portable exe on the [releases page](https://github.com/mayaa2006/tes4-env-editor/releases).

## 0.4.0

- **Word Splicer as a Windows program.** `WordSplicer-0.4.0-windows.zip` on this release: unzip and double-click `WordSplicer.exe`. A small window asks for the folder of voice lines (and, optionally, the swap plan and where to keep your work), remembers them for next time, and opens the screen in your browser when you press Start. The first time you find words it downloads a speech model (about 140 MB). The build checks the finished program starts, serves a line, opens its window and loads the speech libraries before it is published. The screen also now says so while the speech model downloads instead of looking stuck.
- **Find lines.** A search box above the list of lines finds them by voice file name (any part, any case, or a whole pasted Windows path), by voice (e.g. `breton/m`), by the expected wording, or by the words heard in the line; several words must all match, matches are highlighted, Enter opens the first result and Esc clears. A voice menu narrows the list to one race and sex.

## 0.3.0

- **Word Splicer (`tools/wordsplice`).** A small program that replaces single words inside existing voice lines with clips you provide. Add clips of words (she, daughter, Ariella…) with as many takes as you like; it finds where each word is spoken in the lines, highlights the ones to replace (he, son, Martin…), and splices your clip in with a short cross-fade, matching loudness. Choose a take per word, play the result, nudge or drag the cut points, undo, and save the finished line as an .mp3 in the same folder layout. Auto-fill does every line that has the clips it needs. Runs on your computer only; on Windows `start.bat` sets it up.

## 0.2.0

- **Oblivion plugin reader and writer.** Reads `Oblivion.esm` (20-byte headers, compressed records) and writes it back byte for byte.
- **Character swap, first version.** `npm run tes4 -- swap-scan` finds a character (Martin by default) and lists every spoken line with its audio file name, every line where someone else says the name, and every other text that carries the name. It writes a recording script, a summary and an editable plan. `swap-build` writes an override `.esp` with the new names, subtitles and the character made female. Gendered words are flagged and only rewritten when you accept the suggestions. It also reads the voice archives (`Oblivion - Voices*.bsa`), confirms each audio file exists, and with `--extract` copies the originals out for splicing. The Windows app itself does not have this yet.

## 0.1.0

- **Starting point.** This repository begins as a copy of the Skyrim editor (TES5 Env Editor). It does not read Oblivion plugins yet. Coming next: an Oblivion (TES4) plugin reader and a character-swap tool that finds a character's name, dialogue subtitles and voice files so they can be replaced (first goal: Martin Septim to Ariella Septim).
