import type { Tes4Plugin, PluginRecord } from '../plugin';
import { GroupTypes } from '../plugin';
import { decodeText } from '../text';
import type { EditRef, SwapPlan, SwapPreset, TextEdit, VoiceEntry } from './types';

const GET_IS_ID = 72;
const hex8 = (n: number) => n.toString(16).toUpperCase().padStart(8, '0');
const edid = (r: PluginRecord) => {
  const s = r.first('EDID');
  return s ? decodeText(s.data) : '';
};
const u32 = (d: Uint8Array, at: number) => new DataView(d.buffer, d.byteOffset, d.byteLength).getUint32(at, true);

export function applyNames(text: string, preset: SwapPreset): string {
  let out = text;
  for (const r of preset.names) out = out.replace(new RegExp(r.from, 'g'), r.to);
  return out;
}

function genderedWords(text: string, preset: SwapPreset): string[] {
  const found: string[] = [];
  for (const g of preset.gendered) if (new RegExp(`\\b${g.from}\\b`, 'i').test(text)) found.push(g.from);
  return found;
}

function suggest(text: string, preset: SwapPreset): string {
  let out = text;
  for (const g of preset.gendered) {
    out = out.replace(new RegExp(`\\b${g.from}\\b`, 'gi'), (m) => (m[0] === m[0]!.toUpperCase() && m[0] !== m[0]!.toLowerCase() ? g.to[0]!.toUpperCase() + g.to.slice(1) : g.to));
  }
  return out;
}

/**
 * Does this dialogue line's conditions say the character speaks it? That means GetIsID == 1 running
 * on the speaker, and not joined with OR to other conditions (which would make it a shared line
 * that other characters say too).
 */
function speakerOf(info: PluginRecord, npcId: number): 'only' | 'shared' | 'no' {
  const conds = info.subs.filter((s) => s.sig === 'CTDA' && s.data.length >= 20);
  let result: 'only' | 'shared' | 'no' = 'no';
  conds.forEach((s, i) => {
    const type = s.data[0]!;
    const compare = new DataView(s.data.buffer, s.data.byteOffset).getFloat32(4, true);
    if (u32(s.data, 8) !== GET_IS_ID || u32(s.data, 12) !== npcId || (type & 0xe0) !== 0 || (type & 0x02) !== 0 || compare !== 1) return;
    const joinedByOr = (type & 1) === 1 || (i > 0 && (conds[i - 1]!.data[0]! & 1) === 1);
    if (joinedByOr) result = result === 'only' ? 'only' : 'shared';
    else result = 'only';
  });
  return result;
}

export function scanSwap(plugin: Tes4Plugin, preset: SwapPreset): SwapPlan {
  const nameRe = new RegExp(`\\b${preset.nameWord}\\b`);
  const editorIds = new Map<number, string>();
  const infos: { rec: PluginRecord; dial: number }[] = [];
  const records: PluginRecord[] = [];
  let npc: PluginRecord | undefined;

  plugin.walk((rec, groups) => {
    if (rec.sig === 'INFO') {
      const g = groups[groups.length - 1];
      infos.push({ rec, dial: g && g.groupType === GroupTypes.TopicChildren ? g.label : 0 });
      return;
    }
    if (rec.sig === 'REFR' || rec.sig === 'ACHR' || rec.sig === 'ACRE' || rec.sig === 'LAND' || rec.sig === 'PGRD' || rec.sig === 'CELL') return;
    records.push(rec);
    if (rec.sig === 'QUST' || rec.sig === 'DIAL' || rec.sig === 'RACE') editorIds.set(rec.formId, edid(rec));
    if (rec.sig === 'NPC_' && edid(rec) === preset.npcEditorId) npc = rec;
  });
  if (!npc) throw new Error(`No NPC with editor ID "${preset.npcEditorId}" in this plugin`);
  const npcRec: PluginRecord = npc;

  const acbs = npcRec.first('ACBS');
  const rnam = npcRec.first('RNAM');
  const race = rnam ? (editorIds.get(u32(rnam.data, 0)) ?? '') : '';
  const female = acbs ? (u32(acbs.data, 0) & 1) === 1 : false;
  const fullSub = npcRec.first('FULL');
  const plan: SwapPlan = {
    preset,
    npc: { formId: npcRec.formId, editorId: preset.npcEditorId, name: fullSub ? decodeText(fullSub.data) : '', race, female, hasFaceData: !!npcRec.first('FGGS') },
    edits: [],
    voice: [],
    pronounOnly: [],
    reportOnly: [],
  };

  const addEdit = (rec: PluginRecord, sub: string, index: number, original: string, proposed: string, withGender: boolean): TextEdit => {
    const gendered = withGender ? genderedWords(original, preset) : [];
    const ref: EditRef = { sig: rec.sig, formId: rec.formId, editorId: edid(rec), sub, index };
    const e: TextEdit = {
      ...ref,
      id: `${rec.sig}:${hex8(rec.formId)}:${sub}:${index}`,
      original,
      proposed,
      status: proposed === original && !gendered.length ? 'none' : gendered.length ? 'review' : 'auto',
      gendered,
    };
    if (gendered.length) e.suggestion = suggest(proposed, preset);
    plan.edits.push(e);
    return e;
  };

  // The character's own record: name, and sex when asked.
  if (fullSub) addEdit(npcRec, 'FULL', 0, plan.npc.name, preset.npcNewName, false);

  // Dialogue.
  const speakerQuests = new Map<number, number>();
  const speakerInfos = new Set<number>();
  const sharedInfos = new Set<number>();
  for (const { rec } of infos) {
    const who = speakerOf(rec, npcRec.formId);
    if (who === 'shared') sharedInfos.add(rec.formId);
    if (who !== 'only') continue;
    speakerInfos.add(rec.formId);
    const q = rec.first('QSTI');
    if (q) speakerQuests.set(u32(q.data, 0), (speakerQuests.get(u32(q.data, 0)) ?? 0) + 1);
  }

  for (const { rec, dial } of infos) {
    const speaks = speakerInfos.has(rec.formId);
    const shared = sharedInfos.has(rec.formId);
    const q = rec.first('QSTI');
    const quest = q ? (editorIds.get(u32(q.data, 0)) ?? '') : '';
    const topic = editorIds.get(dial) ?? '';
    let respNo = 0;
    let nam1 = 0;
    let curNotes = '';
    const subs = rec.subs;
    for (let i = 0; i < subs.length; i++) {
      const s = subs[i]!;
      if (s.sig === 'TRDT') respNo = s.data.length >= 13 ? s.data[12]! : respNo + 1;
      if (s.sig !== 'NAM1') continue;
      const text = decodeText(s.data);
      const next = subs[i + 1];
      curNotes = next && next.sig === 'NAM2' ? decodeText(next.data) : '';
      const hasName = nameRe.test(text);
      if (!speaks && !shared && !hasName) {
        if (speakerQuests.get(q ? u32(q.data, 0) : -1)! >= 3 && genderedWords(text, preset).length) {
          plan.pronounOnly.push({ editId: `INFO:${hex8(rec.formId)}:NAM1:${nam1}`, quest, text });
        }
        nam1++;
        continue;
      }
      if (shared && !hasName) {
        nam1++;
        continue; // said by several characters; nothing to change unless the name is spoken
      }
      const edit = addEdit(rec, 'NAM1', nam1, text, applyNames(text, preset), !speaks);
      if (edit.status === 'none') plan.edits.pop();
      const entry: VoiceEntry = {
        editId: `INFO:${hex8(rec.formId)}:NAM1:${nam1}`,
        infoId: rec.formId,
        quest,
        topic,
        response: respNo,
        kind: speaks ? 'voice' : 'name',
        file: `${quest}_${topic}_${hex8(rec.formId)}_${respNo}`,
        subtitle: edit.proposed,
        originalSubtitle: text,
        notes: curNotes,
      };
      plan.voice.push(entry);
      nam1++;
    }
  }

  // Other text that carries the name.
  const textSubs: Record<string, string[]> = {
    QUST: ['FULL', 'CNAM'],
    DIAL: ['FULL'],
    BOOK: ['DESC', 'FULL'],
    LSCR: ['DESC'],
    FACT: ['FULL'],
    NPC_: [],
  };
  for (const rec of records) {
    for (const key of textSubs[rec.sig] ?? []) {
      let idx = 0;
      for (const s of rec.subs) {
        if (s.sig !== key) continue;
        const text = decodeText(s.data);
        if (nameRe.test(text)) addEdit(rec, key, idx, text, applyNames(text, preset), true);
        idx++;
      }
    }
    if ((rec.sig === 'SCPT' || rec.sig === 'QUST') && rec.subs.some((s) => s.sig === 'SCTX' && nameRe.test(decodeText(s.data)))) {
      const s = rec.subs.find((x) => x.sig === 'SCTX' && nameRe.test(decodeText(x.data)))!;
      const t = decodeText(s.data);
      plan.reportOnly.push({ sig: rec.sig, formId: rec.formId, editorId: edid(rec), where: 'script', snippet: t.slice(Math.max(0, t.search(nameRe) - 30), t.search(nameRe) + 50) });
    }
  }
  // Voice folder for the new character.
  const sex = preset.setFemale === undefined ? (plan.npc.female ? 'F' : 'M') : preset.setFemale ? 'F' : 'M';
  for (const v of plan.voice) if (v.kind === 'voice') v.folder = `Sound\\Voice\\Oblivion.esm\\${race}\\${sex}`;
  return plan;
}
