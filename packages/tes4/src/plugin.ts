/**
 * Oblivion (TES4) plugin container: 20-byte record and group headers, zlib-compressed
 * records, and subrecords with 16-bit sizes. Records keep their original bytes until
 * a subrecord is changed, so an untouched plugin writes back byte for byte.
 */
import { unzlibSync, zlibSync } from 'fflate';

export const HEADER_SIZE = 20;
const COMPRESSED = 0x00040000;

export interface Subrecord {
  sig: string;
  data: Uint8Array;
}

const sigOf = (b: Uint8Array, at: number) => String.fromCharCode(b[at]!, b[at + 1]!, b[at + 2]!, b[at + 3]!);

function parseSubrecords(body: Uint8Array): Subrecord[] {
  const view = new DataView(body.buffer, body.byteOffset, body.byteLength);
  const out: Subrecord[] = [];
  let pos = 0;
  let big = -1;
  while (pos + 6 <= body.length) {
    const sig = sigOf(body, pos);
    let size = view.getUint16(pos + 4, true);
    if (sig === 'XXXX') {
      big = view.getUint32(pos + 6, true);
      pos += 10;
      continue;
    }
    if (big >= 0) {
      size = big;
      big = -1;
    }
    out.push({ sig, data: body.subarray(pos + 6, pos + 6 + size) });
    pos += 6 + size;
  }
  return out;
}

export class PluginRecord {
  /** Original on-disk body (compressed if the flag is set). Dropped once the record is edited. */
  private raw: Uint8Array | undefined;
  private parsed: Subrecord[] | undefined;

  constructor(
    readonly sig: string,
    public flags: number,
    readonly formId: number,
    readonly versionControl: number,
    raw: Uint8Array | Subrecord[],
  ) {
    if (raw instanceof Uint8Array) this.raw = raw;
    else this.parsed = raw;
  }

  get compressed(): boolean {
    return (this.flags & COMPRESSED) !== 0;
  }

  get subs(): Subrecord[] {
    if (!this.parsed) {
      let body = this.raw!;
      if (this.compressed) body = unzlibSync(body.subarray(4));
      this.parsed = parseSubrecords(body);
    }
    return this.parsed;
  }

  get modified(): boolean {
    return this.raw === undefined;
  }

  first(sig: string): Subrecord | undefined {
    return this.subs.find((s) => s.sig === sig);
  }

  /** Call after changing `subs` so the record is re-encoded on write. */
  markModified(): void {
    void this.subs;
    this.raw = undefined;
  }

  /** The encoded body as stored on disk. */
  encodeBody(): Uint8Array {
    if (this.raw) return this.raw;
    let total = 0;
    for (const s of this.subs) total += 6 + s.data.length + (s.data.length > 0xffff ? 10 : 0);
    const plain = new Uint8Array(total);
    const view = new DataView(plain.buffer);
    let pos = 0;
    for (const s of this.subs) {
      if (s.data.length > 0xffff) {
        plain.set([0x58, 0x58, 0x58, 0x58], pos);
        view.setUint16(pos + 4, 4, true);
        view.setUint32(pos + 6, s.data.length, true);
        pos += 10;
      }
      for (let i = 0; i < 4; i++) plain[pos + i] = s.sig.charCodeAt(i);
      view.setUint16(pos + 4, s.data.length > 0xffff ? 0 : s.data.length, true);
      plain.set(s.data, pos + 6);
      pos += 6 + s.data.length;
    }
    if (!this.compressed) return plain;
    const z = zlibSync(plain);
    const out = new Uint8Array(4 + z.length);
    new DataView(out.buffer).setUint32(0, plain.length, true);
    out.set(z, 4);
    return out;
  }
}

export interface PluginGroup {
  /** 4 label bytes: a record signature, a FormID or block coordinates, depending on `groupType`. */
  label: number;
  groupType: number;
  stamp: number;
  children: PluginNode[];
}

export type PluginNode = PluginRecord | PluginGroup;
export const isGroup = (n: PluginNode): n is PluginGroup => !(n instanceof PluginRecord);

export const GroupTypes = { Top: 0, TopicChildren: 7 } as const;

export function labelToSig(label: number): string {
  return String.fromCharCode(label & 255, (label >>> 8) & 255, (label >>> 16) & 255, (label >>> 24) & 255);
}

export function sigToLabel(sig: string): number {
  return (sig.charCodeAt(0) | (sig.charCodeAt(1) << 8) | (sig.charCodeAt(2) << 16) | (sig.charCodeAt(3) << 24)) >>> 0;
}

export class Tes4Plugin {
  constructor(
    public header: PluginRecord,
    public nodes: PluginNode[],
  ) {}

  get masters(): string[] {
    return this.header.subs.filter((s) => s.sig === 'MAST').map((s) => new TextDecoder('windows-1252').decode(s.data.subarray(0, Math.max(0, s.data.length - 1))));
  }

  /** Depth-first walk over records. `groups` is the chain of enclosing groups, outermost first. */
  walk(visit: (rec: PluginRecord, groups: readonly PluginGroup[]) => void): void {
    const stack: PluginGroup[] = [];
    const go = (nodes: PluginNode[]) => {
      for (const n of nodes) {
        if (isGroup(n)) {
          stack.push(n);
          go(n.children);
          stack.pop();
        } else visit(n, stack);
      }
    };
    go(this.nodes);
  }

  write(): Uint8Array {
    const parts: Uint8Array[] = [];
    let total = 0;
    const push = (b: Uint8Array) => {
      parts.push(b);
      total += b.length;
    };
    const writeRecord = (r: PluginRecord) => {
      const body = r.encodeBody();
      const h = new Uint8Array(HEADER_SIZE);
      for (let i = 0; i < 4; i++) h[i] = r.sig.charCodeAt(i);
      const v = new DataView(h.buffer);
      v.setUint32(4, body.length, true);
      v.setUint32(8, r.flags, true);
      v.setUint32(12, r.formId, true);
      v.setUint32(16, r.versionControl, true);
      push(h);
      push(body);
    };
    const writeGroup = (g: PluginGroup) => {
      const h = new Uint8Array(HEADER_SIZE);
      h.set([0x47, 0x52, 0x55, 0x50]);
      const v = new DataView(h.buffer);
      v.setUint32(8, g.label, true);
      v.setUint32(12, g.groupType, true);
      v.setUint32(16, g.stamp, true);
      push(h);
      const start = total;
      for (const c of g.children) isGroup(c) ? writeGroup(c) : writeRecord(c);
      v.setUint32(4, HEADER_SIZE + (total - start), true);
    };
    writeRecord(this.header);
    for (const n of this.nodes) isGroup(n) ? writeGroup(n) : writeRecord(n);
    const out = new Uint8Array(total);
    let at = 0;
    for (const p of parts) {
      out.set(p, at);
      at += p.length;
    }
    return out;
  }
}

export function parseTes4(bytes: Uint8Array, fileName = 'plugin'): Tes4Plugin {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < HEADER_SIZE || sigOf(bytes, 0) !== 'TES4') throw new Error(`${fileName}: not an Oblivion plugin (no TES4 header)`);

  const readRecord = (pos: number): [PluginRecord, number] => {
    const size = view.getUint32(pos + 4, true);
    const end = pos + HEADER_SIZE + size;
    if (end > bytes.length) throw new Error(`${fileName}: record at ${pos} runs past the end of the file`);
    const rec = new PluginRecord(sigOf(bytes, pos), view.getUint32(pos + 8, true), view.getUint32(pos + 12, true), view.getUint32(pos + 16, true), bytes.subarray(pos + HEADER_SIZE, end));
    return [rec, end];
  };

  const readNodes = (pos: number, end: number): PluginNode[] => {
    const out: PluginNode[] = [];
    while (pos < end) {
      if (sigOf(bytes, pos) === 'GRUP') {
        const size = view.getUint32(pos + 4, true);
        if (size < HEADER_SIZE || pos + size > end) throw new Error(`${fileName}: group at ${pos} has a bad size`);
        out.push({
          label: view.getUint32(pos + 8, true),
          groupType: view.getUint32(pos + 12, true),
          stamp: view.getUint32(pos + 16, true),
          children: readNodes(pos + HEADER_SIZE, pos + size),
        });
        pos += size;
      } else {
        const [rec, next] = readRecord(pos);
        out.push(rec);
        pos = next;
      }
    }
    return out;
  };

  const [header, afterHeader] = readRecord(0);
  return new Tes4Plugin(header, readNodes(afterHeader, bytes.length));
}
