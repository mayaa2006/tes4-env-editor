/** What to swap, and how names and gendered words should read afterwards. */
export interface SwapPreset {
  /** Editor ID of the character being replaced, e.g. "Martin". */
  npcEditorId: string;
  /** New display name for the character's own NPC record. */
  npcNewName: string;
  /** Made female (true), male (false) or left as it is (undefined). */
  setFemale?: boolean;
  /** Name rewrites, tried in order on every piece of text. `from` is a regular expression. */
  names: { from: string; to: string }[];
  /** Gendered words flagged in text about the character, and what to suggest instead. */
  gendered: { from: string; to: string }[];
  /** Records are only edited when their text matches one of these (besides dialogue). */
  nameWord: string;
}

export interface EditRef {
  sig: string;
  formId: number;
  editorId: string;
  /** Subrecord signature, e.g. "NAM1", and which one of that signature (0 = first). */
  sub: string;
  index: number;
}

/** One piece of text that changes. */
export interface TextEdit extends EditRef {
  id: string;
  original: string;
  /** Edit this to change what the tool writes. */
  proposed: string;
  /**
   * "auto": only the name changes. "review": gendered words were found and a suggestion
   * is included; the suggestion is only written when you accept it. "none": nothing to change.
   */
  status: 'auto' | 'review' | 'none';
  gendered: string[];
  suggestion?: string;
}

/** One spoken response: the audio file that goes with a subtitle. */
export interface VoiceEntry {
  editId: string;
  infoId: number;
  quest: string;
  topic: string;
  response: number;
  /** "voice": the character's own line, record the whole thing. "name": someone else says the name, splice it in. */
  kind: 'voice' | 'name';
  file: string;
  /** Voice folder for the new character (voice lines) when known. */
  folder?: string;
  subtitle: string;
  originalSubtitle: string;
  notes: string;
}

export interface SwapPlan {
  preset: SwapPreset;
  npc: { formId: number; editorId: string; name: string; race: string; female: boolean; hasFaceData: boolean };
  edits: TextEdit[];
  voice: VoiceEntry[];
  /** Lines that talk about the character with a gendered word but no name (not edited). */
  pronounOnly: { editId: string; quest: string; text: string }[];
  /** Places the name shows up that the tool can't change (scripts, editor IDs...). */
  reportOnly: { sig: string; formId: number; editorId: string; where: string; snippet: string }[];
}
