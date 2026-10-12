import { describe, expect, it } from 'vitest';
import { BsaArchive, attachVoiceFiles, indexVoice, type SwapPlan, type VoiceEntry } from '../src/index';

/** A tiny Oblivion BSA (v103, uncompressed) with the given files, all in one folder. */
function makeBsa(folder: string, files: Record<string, string>): Uint8Array {
  const names = Object.keys(files);
  const folderRecord = 16;
  const folderBlock = 1 + folder.length + 1 + names.length * 16;
  const fileNames = names.map((n) => n + '\0').join('');
  const dataStart = 36 + folderRecord + folderBlock + fileNames.length;
  const out = new Uint8Array(dataStart + names.reduce((n, k) => n + files[k]!.length, 0));
  const v = new DataView(out.buffer);
  out.set([0x42, 0x53, 0x41, 0]);
  v.setUint32(4, 103, true);
  v.setUint32(8, 36, true);
  v.setUint32(12, 0x3, true);
  v.setUint32(16, 1, true);
  v.setUint32(20, names.length, true);
  v.setUint32(24, folder.length + 1, true);
  v.setUint32(28, fileNames.length, true);
  v.setUint32(36 + 8, names.length, true);
  v.setUint32(36 + 12, 36 + folderRecord + fileNames.length, true);
  let p = 36 + folderRecord;
  out[p++] = folder.length + 1;
  for (const c of folder) out[p++] = c.charCodeAt(0);
  p++;
  let data = dataStart;
  for (const n of names) {
    v.setUint32(p + 8, files[n]!.length, true);
    v.setUint32(p + 12, data, true);
    for (const c of files[n]!) out[data++] = c.charCodeAt(0);
    p += 16;
  }
  for (const c of fileNames) out[p++] = c.charCodeAt(0);
  return out;
}

const entry = (file: string, kind: VoiceEntry['kind'] = 'voice'): VoiceEntry => ({ editId: 'x', infoId: 0, quest: '', topic: '', response: 1, kind, file, subtitle: '', originalSubtitle: '', notes: '' });

describe('Oblivion BSA', () => {
  const bytes = makeBsa('Sound\\Voice\\Oblivion.esm\\Imperial\\M', { 'MQ03_Old_0009226A_2.mp3': 'AAAA', 'MQ03_Old_0009226A_2.lip': 'LL', 'MQ00_Greeting_00000010_1.mp3': 'BB' });
  const archive = BsaArchive.fromReader('test.bsa', (o, l) => bytes.subarray(o, o + l));

  it('lists folders and files lower-cased and reads their data', () => {
    expect(archive.entries.map((e) => e.folder + '\\' + e.name)).toContain('sound\\voice\\oblivion.esm\\imperial\\m\\mq00_greeting_00000010_1.mp3');
    const e = archive.entries.find((x) => x.name === 'mq03_old_0009226a_2.mp3')!;
    expect(new TextDecoder().decode(archive.read(e))).toBe('AAAA');
  });

  it('finds audio by name, and by line ID when it is named after an older topic', () => {
    const plan = { voice: [entry('MQ00_Greeting_00000010_1'), entry('MQ03_New_0009226A_2', 'name'), entry('MQ03_New_0009226A_5')] } as SwapPlan;
    attachVoiceFiles(plan, indexVoice([archive]), ['test.bsa']);
    expect(plan.voice[0]!.found).toHaveLength(1);
    expect(plan.voice[1]).toMatchObject({ audioName: 'mq03_old_0009226a_2' });
    expect(plan.voice[1]!.found![0]).toMatchObject({ folder: 'sound\\voice\\oblivion.esm\\imperial\\m', hasLip: true });
    expect(plan.voice[2]!.found).toEqual([]);
    expect(plan.voiceCheck).toMatchObject({ voiceFound: 1, voiceMissing: 1, nameFound: 1, nameMissing: 0 });
  });
});
