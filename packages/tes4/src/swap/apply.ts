import { GroupTypes, PluginRecord, Tes4Plugin, sigToLabel, type PluginGroup, type PluginNode } from '../plugin';
import { encodeText } from '../text';
import { applyNames } from './scan';
import type { SwapPlan, TextEdit } from './types';

export interface ApplyOptions {
  /** Write the suggested wording (him → her...) for edits marked "review". Without it only the name changes. */
  acceptSuggestions?: boolean;
  masterName?: string;
}

export interface ApplyResult {
  plugin: Tes4Plugin;
  /** Edits written, and why any were skipped. */
  written: number;
  skipped: { id: string; reason: string }[];
  notes: string[];
}

/** The text an edit will write: your own wording if you changed it, else the suggestion when accepted, else the name swap. */
export function textFor(edit: TextEdit, plan: SwapPlan, opts: ApplyOptions): string {
  const userEdited = edit.proposed !== applyNames(edit.original, plan.preset);
  if (userEdited) return edit.proposed;
  return edit.status === 'review' && opts.acceptSuggestions && edit.suggestion !== undefined ? edit.suggestion : edit.proposed;
}

/**
 * Build a small override plugin (an .esp that needs the original .esm) holding only the records
 * the plan changes. The original game file is never touched.
 */
export function buildSwapPlugin(source: Tes4Plugin, plan: SwapPlan, opts: ApplyOptions = {}): ApplyResult {
  const master = opts.masterName ?? 'Oblivion.esm';
  const byId = new Map<number, PluginRecord>();
  const dialOf = new Map<number, number>();
  const wanted = new Set<number>(plan.edits.map((e) => e.formId));
  wanted.add(plan.npc.formId);
  const order: string[] = source.nodes.map((n) => ('children' in n ? String.fromCharCode(n.label & 255, (n.label >>> 8) & 255, (n.label >>> 16) & 255, (n.label >>> 24) & 255) : ''));
  source.walk((rec, groups) => {
    if (rec.sig === 'INFO') {
      if (!wanted.has(rec.formId)) return;
      const g = groups[groups.length - 1];
      if (g && g.groupType === GroupTypes.TopicChildren) dialOf.set(rec.formId, g.label);
    }
    if (rec.sig === 'DIAL' || wanted.has(rec.formId)) byId.set(rec.formId, rec);
  });

  const out = new Map<number, PluginRecord>();
  const skipped: ApplyResult['skipped'] = [];
  const notes: string[] = [];
  let written = 0;
  const copy = (rec: PluginRecord) => {
    let c = out.get(rec.formId);
    if (!c) {
      c = new PluginRecord(rec.sig, rec.flags, rec.formId, rec.versionControl, rec.subs.map((s) => ({ sig: s.sig, data: s.data })));
      out.set(rec.formId, c);
    }
    return c;
  };

  for (const e of plan.edits) {
    const rec = byId.get(e.formId);
    if (!rec || rec.sig !== e.sig) {
      skipped.push({ id: e.id, reason: 'record not found in the game file' });
      continue;
    }
    const target = copy(rec);
    const matches = target.subs.filter((s) => s.sig === e.sub);
    const sub = matches[e.index];
    if (!sub) {
      skipped.push({ id: e.id, reason: `no ${e.sub} #${e.index} in the record` });
      continue;
    }
    sub.data = encodeText(textFor(e, plan, opts));
    target.markModified();
    written++;
  }

  if (plan.preset.setFemale !== undefined) {
    const npc = byId.get(plan.npc.formId);
    if (npc) {
      const target = copy(npc);
      const acbs = target.subs.find((s) => s.sig === 'ACBS');
      if (acbs) {
        const d = new Uint8Array(acbs.data);
        const v = new DataView(d.buffer);
        v.setUint32(0, plan.preset.setFemale ? v.getUint32(0, true) | 1 : v.getUint32(0, true) & ~1, true);
        acbs.data = d;
        target.markModified();
        notes.push(`${plan.npc.editorId} is now ${plan.preset.setFemale ? 'female' : 'male'}.`);
        if (plan.npc.hasFaceData) notes.push('Face and body still use the original character\'s face data; redo the face (race, hair, face morphs) in the Construction Set.');
      }
    }
  }

  // Lay the records out in the same group structure the game file uses.
  const topFor = (sig: string): PluginGroup => ({ label: sigToLabel(sig), groupType: GroupTypes.Top, stamp: 0, children: [] });
  const tops = new Map<string, PluginGroup>();
  const top = (sig: string) => {
    let g = tops.get(sig);
    if (!g) tops.set(sig, (g = topFor(sig)));
    return g;
  };
  const dials = new Map<number, PluginRecord[]>();
  for (const rec of out.values()) {
    if (rec.sig === 'INFO') {
      const d = dialOf.get(rec.formId);
      if (d === undefined) {
        skipped.push({ id: `INFO:${rec.formId}`, reason: 'topic not found' });
        continue;
      }
      dials.set(d, [...(dials.get(d) ?? []), rec]);
    } else if (rec.sig !== 'DIAL') top(rec.sig).children.push(rec);
  }
  const dialIds = new Set<number>([...dials.keys(), ...[...out.values()].filter((r) => r.sig === 'DIAL').map((r) => r.formId)]);
  for (const id of dialIds) {
    const dial = out.get(id) ?? byId.get(id);
    if (!dial) continue;
    const g = top('DIAL');
    g.children.push(dial);
    const kids = dials.get(id);
    if (kids) g.children.push({ label: id, groupType: GroupTypes.TopicChildren, stamp: 0, children: kids } satisfies PluginGroup);
  }
  const nodes: PluginNode[] = [...tops.values()].sort((a, b) => order.indexOf(labelName(a)) - order.indexOf(labelName(b)));

  let count = 0;
  const tally = (ns: PluginNode[]) => {
    for (const n of ns) {
      count++;
      if ('children' in n) tally(n.children);
    }
  };
  tally(nodes);
  const hedr = new Uint8Array(12);
  const hv = new DataView(hedr.buffer);
  hv.setFloat32(0, 1.0, true);
  hv.setUint32(4, count, true);
  hv.setUint32(8, 0x800, true);
  const header = new PluginRecord('TES4', 0, 0, 0, [
    { sig: 'HEDR', data: hedr },
    { sig: 'CNAM', data: encodeText('tes4-env-editor') },
    { sig: 'SNAM', data: encodeText(`Character swap: ${plan.npc.editorId} to ${plan.preset.npcNewName}`) },
    { sig: 'MAST', data: encodeText(master) },
    { sig: 'DATA', data: new Uint8Array(8) },
  ]);
  return { plugin: new Tes4Plugin(header, nodes), written, skipped, notes };
}

function labelName(g: PluginGroup): string {
  return String.fromCharCode(g.label & 255, (g.label >>> 8) & 255, (g.label >>> 16) & 255, (g.label >>> 24) & 255);
}
