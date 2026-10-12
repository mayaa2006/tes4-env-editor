/**
 * Oblivion BSA archives (version 103). Only the table of contents is read up front, so a
 * 1 GB voice archive opens instantly; file data is read on demand.
 */
import { closeSync, openSync, readSync } from 'node:fs';
import { unzlibSync } from 'fflate';

export interface BsaEntry {
  /** Lower-case, backslash-separated folder, e.g. "sound\\voice\\oblivion.esm\\imperial\\m". */
  folder: string;
  /** Lower-case file name with extension. */
  name: string;
  size: number;
  offset: number;
  compressed: boolean;
}

export type ReadAt = (offset: number, length: number) => Uint8Array;

const COMPRESSED_ARCHIVE = 0x4;

export class BsaArchive {
  readonly entries: BsaEntry[] = [];
  private constructor(
    readonly path: string,
    private readAt: ReadAt,
    private archiveCompressed: boolean,
  ) {}

  static open(path: string): BsaArchive {
    const fd = openSync(path, 'r');
    const readAt: ReadAt = (offset, length) => {
      const buf = Buffer.alloc(length);
      let got = 0;
      while (got < length) {
        const n = readSync(fd, buf, got, length - got, offset + got);
        if (n <= 0) break;
        got += n;
      }
      return new Uint8Array(buf.buffer, buf.byteOffset, got);
    };
    try {
      const archive = BsaArchive.fromReader(path, readAt);
      archive.closeFile = () => closeSync(fd);
      return archive;
    } catch (e) {
      closeSync(fd);
      throw e;
    }
  }

  private closeFile: () => void = () => {};

  /** Release the file handle (archives opened from a path keep it open for reads). */
  close(): void {
    this.closeFile();
    this.closeFile = () => {};
  }

  /** Parse an archive from any random-access reader (used by tests). */
  static fromReader(path: string, readAt: ReadAt): BsaArchive {
    const head = readAt(0, 36);
    const hv = new DataView(head.buffer, head.byteOffset, head.byteLength);
    if (head.length < 36 || String.fromCharCode(head[0]!, head[1]!, head[2]!) !== 'BSA' || hv.getUint32(4, true) !== 103) throw new Error(`${path}: not an Oblivion BSA (version 103)`);
    const folderOffset = hv.getUint32(8, true);
    const flags = hv.getUint32(12, true);
    const folderCount = hv.getUint32(16, true);
    const fileCount = hv.getUint32(20, true);
    const folderNamesLength = hv.getUint32(24, true);
    const fileNamesLength = hv.getUint32(28, true);
    const archive = new BsaArchive(path, readAt, (flags & COMPRESSED_ARCHIVE) !== 0);

    // Folder records, then for each folder its name and file records, then the file name block.
    const tocLength = folderCount * 16 + folderNamesLength + folderCount + fileCount * 16 + fileNamesLength;
    const toc = readAt(folderOffset, tocLength);
    const v = new DataView(toc.buffer, toc.byteOffset, toc.byteLength);
    const folders: { count: number }[] = [];
    for (let i = 0; i < folderCount; i++) folders.push({ count: v.getUint32(i * 16 + 8, true) });
    let pos = folderCount * 16;
    const latin1 = new TextDecoder('windows-1252');
    const pending: { folder: string; size: number; offset: number }[] = [];
    for (const f of folders) {
      const len = toc[pos]!;
      const folder = latin1.decode(toc.subarray(pos + 1, pos + len)).toLowerCase().replace(/\//g, '\\');
      pos += 1 + len;
      for (let i = 0; i < f.count; i++) {
        pending.push({ folder, size: v.getUint32(pos + 8, true), offset: v.getUint32(pos + 12, true) });
        pos += 16;
      }
    }
    const names = toc.subarray(pos, pos + fileNamesLength);
    let np = 0;
    for (const p of pending) {
      let end = np;
      while (end < names.length && names[end] !== 0) end++;
      const name = latin1.decode(names.subarray(np, end)).toLowerCase();
      np = end + 1;
      const toggle = (p.size & 0x40000000) !== 0;
      archive.entries.push({ folder: p.folder, name, size: p.size & 0x3fffffff, offset: p.offset, compressed: archive.archiveCompressed !== toggle });
    }
    return archive;
  }

  /** The file's bytes (decompressed). */
  read(entry: BsaEntry): Uint8Array {
    const raw = this.readAt(entry.offset, entry.size);
    if (!entry.compressed) return raw;
    return unzlibSync(raw.subarray(4));
  }
}
