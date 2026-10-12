# Roadmap

- [x] Oblivion (TES4) plugin container reader and writer (20-byte headers, compressed records); byte-exact on `Oblivion.esm`
- [ ] Oblivion record definitions for a form editor (only the fields the swap needs are decoded)
- [x] Find every mention of a character (NPC, dialogue, quest journal, books, topics, factions, scripts)
- [x] List a character's voice files with their subtitles (file names computed; to be checked against the voice BSAs)
- [x] Bulk rename and subtitle edit written to an override `.esp`, with gendered-word suggestions
- [ ] Preview and undo in the app (command line only for now)
- [x] Recording script with exact target filenames and the female voice folder
- [x] Read Oblivion BSA (v103) voice archives: confirm each file exists, find the folders others' lines live in, copy originals to splice
- [x] Word Splicer: replace single words in existing voice lines with your own clips (several takes per word, per-word choice, auto-fill, undo)
- [ ] Put the spliced/new audio back and check every file in the recording script is present
- [ ] Word Splicer: use the swap plan to fill in exactly the words each subtitle changes
- [ ] List the `.lip` files that need regenerating
