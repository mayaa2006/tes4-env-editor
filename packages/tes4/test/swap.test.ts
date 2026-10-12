import { describe, expect, it } from 'vitest';
import { GroupTypes, PluginRecord, Tes4Plugin, buildSwapPlugin, decodeText, encodeText, MARTIN_TO_ARIELLA, parseTes4, scanSwap, sigToLabel, type PluginNode, type Subrecord } from '../src/index';

const sub = (sig: string, data: Uint8Array): Subrecord => ({ sig, data });
const str = (sig: string, s: string) => sub(sig, encodeText(s));
const u32 = (...v: number[]) => {
  const d = new Uint8Array(v.length * 4);
  v.forEach((x, i) => new DataView(d.buffer).setUint32(i * 4, x >>> 0, true));
  return d;
};
const ctda = (fn: number, p1: number, type = 0, value = 1) => {
  const d = new Uint8Array(24);
  const v = new DataView(d.buffer);
  d[0] = type;
  v.setFloat32(4, value, true);
  v.setUint32(8, fn, true);
  v.setUint32(12, p1, true);
  return sub('CTDA', d);
};
const trdt = (n: number) => {
  const d = new Uint8Array(16);
  d[12] = n;
  return sub('TRDT', d);
};
const MARTIN = 0x33907;
const group = (sig: string, children: PluginNode[]): PluginNode => ({ label: sigToLabel(sig), groupType: GroupTypes.Top, stamp: 0, children });

function fixture(): Tes4Plugin {
  const info = (id: number, conds: Subrecord[], text: string, compressed = false) =>
    new PluginRecord('INFO', compressed ? 0x40000 : 0, id, 0, [sub('QSTI', u32(0x100)), ...conds, trdt(1), str('NAM1', text), str('NAM2', '')]);
  return new Tes4Plugin(new PluginRecord('TES4', 1, 0, 0, [sub('HEDR', new Uint8Array(12))]), [
    group('RACE', [new PluginRecord('RACE', 0, 0x200, 0, [str('EDID', 'Imperial')])]),
    group('NPC_', [
      new PluginRecord('NPC_', 0, MARTIN, 0, [str('EDID', 'Martin'), str('FULL', 'Brother Martin'), sub('ACBS', u32(0, 0)), sub('RNAM', u32(0x200))]),
      new PluginRecord('NPC_', 0, 0x34eb5, 0, [str('EDID', 'MartinaFloria'), str('FULL', 'Martina Floria'), sub('ACBS', u32(0, 0))]),
    ]),
    group('QUST', [new PluginRecord('QUST', 0, 0x100, 0, [str('EDID', 'MQ00'), str('CNAM', 'Talk to Martin. He is waiting.')])]),
    group('DIAL', [
      new PluginRecord('DIAL', 0, 0x300, 0, [str('EDID', 'GREETING')]),
      { label: 0x300, groupType: GroupTypes.TopicChildren, stamp: 0, children: [
        info(0x1001, [ctda(72, MARTIN)], 'I am Martin.', true),
        info(0x1002, [ctda(72, MARTIN, 1), ctda(72, 0x999)], 'Shared line.'),
        info(0x1003, [], 'Tell Martina Floria that Martin will be late; he is busy.'),
        info(0x1004, [], 'Nothing to see.'),
      ] },
    ]),
  ]);
}

describe('Oblivion plugin container', () => {
  it('round-trips byte for byte, including compressed records', () => {
    const bytes = fixture().write();
    expect(parseTes4(bytes).write()).toEqual(bytes);
  });
});

describe('character swap', () => {
  const plan = scanSwap(fixture(), MARTIN_TO_ARIELLA);

  it('finds the character, and does not confuse Martina with Martin', () => {
    expect(plan.npc).toMatchObject({ editorId: 'Martin', race: 'Imperial', female: false });
    expect(plan.edits.find((e) => e.formId === 0x34eb5)).toBeUndefined();
    expect(plan.edits.find((e) => e.formId === MARTIN)!.proposed).toBe('Sister Ariella');
  });

  it('lists the character\'s own lines as voice to record, in the female folder, with the file name', () => {
    const v = plan.voice.filter((x) => x.kind === 'voice');
    expect(v).toHaveLength(1);
    expect(v[0]).toMatchObject({ file: 'MQ00_GREETING_00001001_1', folder: 'Sound\\Voice\\Oblivion.esm\\Imperial\\F', subtitle: 'I am Ariella.' });
  });

  it('treats lines shared through OR conditions as other people\'s', () => {
    expect(plan.voice.find((x) => x.infoId === 0x1002)).toBeUndefined();
  });

  it('lists lines where someone else says the name, flags gendered words, and suggests a rewrite', () => {
    const e = plan.edits.find((x) => x.formId === 0x1003)!;
    expect(plan.voice.find((x) => x.infoId === 0x1003)!.kind).toBe('name');
    expect(e.proposed).toBe('Tell Martina Floria that Ariella will be late; he is busy.');
    expect(e.status).toBe('review');
    expect(e.suggestion).toBe('Tell Martina Floria that Ariella will be late; she is busy.');
  });

  it('builds an override plugin with only the changed records', () => {
    const res = buildSwapPlugin(fixture(), plan, { acceptSuggestions: true });
    const esp = parseTes4(res.plugin.write());
    expect(esp.masters).toEqual(['Oblivion.esm']);
    const seen = new Map<number, PluginRecord>();
    esp.walk((r) => seen.set(r.formId, r));
    expect([...seen.keys()].sort((a, b) => a - b)).toEqual([0x100, 0x300, 0x1001, 0x1003, MARTIN].sort((a, b) => a - b));
    expect(decodeText(seen.get(MARTIN)!.first('FULL')!.data)).toBe('Sister Ariella');
    expect(new DataView(seen.get(MARTIN)!.first('ACBS')!.data.buffer, seen.get(MARTIN)!.first('ACBS')!.data.byteOffset).getUint32(0, true) & 1).toBe(1);
    expect(decodeText(seen.get(0x1001)!.first('NAM1')!.data)).toBe('I am Ariella.');
    expect(decodeText(seen.get(0x1003)!.first('NAM1')!.data)).toContain('she is busy');
    expect(decodeText(seen.get(0x100)!.first('CNAM')!.data)).toBe('Talk to Ariella. She is waiting.');
  });

  it('only changes the name when suggestions are not accepted, and keeps your own wording', () => {
    const mine = structuredClone(plan);
    mine.edits.find((x) => x.formId === 0x1003)!.status = 'review';
    mine.edits.find((x) => x.formId === 0x1001)!.proposed = 'Call me Ari.';
    const res = buildSwapPlugin(fixture(), mine);
    const seen = new Map<number, PluginRecord>();
    res.plugin.walk((r) => seen.set(r.formId, r));
    expect(decodeText(seen.get(0x1003)!.first('NAM1')!.data)).toContain('he is busy');
    expect(decodeText(seen.get(0x1001)!.first('NAM1')!.data)).toBe('Call me Ari.');
  });
});
