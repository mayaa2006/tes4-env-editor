/** Oblivion strings are Windows-1252 and NUL-terminated. */

const decoder = new TextDecoder('windows-1252');

/** Characters in 0x80-0x9F that differ from Latin-1 (curly quotes, dashes...). */
const encodeSpecials = new Map<string, number>();
for (let b = 0x80; b < 0xa0; b++) {
  const ch = decoder.decode(new Uint8Array([b]));
  if (ch !== '�') encodeSpecials.set(ch, b);
}

export function decodeText(bytes: Uint8Array): string {
  let end = bytes.indexOf(0);
  if (end < 0) end = bytes.length;
  return decoder.decode(bytes.subarray(0, end));
}

/** Encode with a trailing NUL. Characters Windows-1252 can't hold become "?". */
export function encodeText(text: string): Uint8Array {
  const out = new Uint8Array(text.length + 1);
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    out[i] = c < 0x80 || (c >= 0xa0 && c < 0x100) ? c : (encodeSpecials.get(text[i]!) ?? 0x3f);
  }
  return out;
}
