import type { BsaArchive, BsaEntry } from '../bsa';
import type { SwapPlan, VoiceEntry } from './types';

export interface VoiceIndex {
  byName: Map<string, { entry: BsaEntry; archive: BsaArchive }[]>;
  /** Same entries keyed by "<line id>_<response>.<ext>", for audio named after an older topic. */
  byLine: Map<string, { entry: BsaEntry; archive: BsaArchive }[]>;
}

const lineKey = (name: string) => /_([0-9a-f]{8}_\d+\.[a-z0-9]+)$/.exec(name)?.[1];

export function indexVoice(archives: BsaArchive[]): VoiceIndex {
  const byName = new Map<string, { entry: BsaEntry; archive: BsaArchive }[]>();
  const byLine = new Map<string, { entry: BsaEntry; archive: BsaArchive }[]>();
  for (const archive of archives) {
    for (const entry of archive.entries) {
      if (!entry.folder.startsWith('sound\\voice\\')) continue;
      const list = byName.get(entry.name);
      if (list) list.push({ entry, archive });
      else byName.set(entry.name, [{ entry, archive }]);
      const key = lineKey(entry.name);
      if (key) byLine.set(key, [...(byLine.get(key) ?? []), { entry, archive }]);
    }
  }
  return { byName, byLine };
}

/** Where each response's original audio is, using the lower-case `quest_topic_formid_n` file name. */
export function attachVoiceFiles(plan: SwapPlan, index: VoiceIndex, archiveNames: string[]): void {
  let voiceFound = 0, voiceMissing = 0, nameFound = 0, nameMissing = 0;
  for (const v of plan.voice) {
    const base = v.file.toLowerCase();
    let mp3 = index.byName.get(`${base}.mp3`) ?? [];
    if (!mp3.length) {
      const key = lineKey(`${base}.mp3`);
      mp3 = (key && index.byLine.get(key)) || [];
      if (mp3.length) v.audioName = mp3[0]!.entry.name.replace(/\.mp3$/, '');
    }
    v.found = mp3.map(({ entry, archive }) => ({
      folder: entry.folder,
      archive: archive.path,
      hasLip: (index.byName.get(`${(v.audioName ?? base).toLowerCase()}.lip`) ?? []).some((l) => l.entry.folder === entry.folder),
    }));
    const ok = v.found.length > 0;
    if (v.kind === 'voice') ok ? voiceFound++ : voiceMissing++;
    else ok ? nameFound++ : nameMissing++;
  }
  plan.voiceCheck = { archives: archiveNames, voiceFound, voiceMissing, nameFound, nameMissing };
}

/** The archive entries for one response: its .mp3 (and .lip) in every folder it exists in. */
export function voiceEntries(v: VoiceEntry, index: VoiceIndex): { entry: BsaEntry; archive: BsaArchive }[] {
  const base = (v.audioName ?? v.file).toLowerCase();
  return [...(index.byName.get(`${base}.mp3`) ?? []), ...(index.byName.get(`${base}.lip`) ?? [])];
}
