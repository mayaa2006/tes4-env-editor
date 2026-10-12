#!/usr/bin/env node
/**
 * tes4 — Oblivion plugin tools.
 *
 *   tes4 swap-scan  <Oblivion.esm> --out <folder> [--voice <bsa>…] [--extract] [--preset martin-to-ariella]
 *   tes4 swap-build <Oblivion.esm> <swap-plan.json> --out <Plugin.esp> [--accept-suggestions]
 */
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { BsaArchive, MARTIN_TO_ARIELLA, attachVoiceFiles, buildSwapPlugin, indexVoice, voiceEntries, parseTes4, planSummaryMarkdown, pronounCheckCsv, recordingScriptCsv, scanSwap, type SwapPlan } from './index';

const PRESETS = { 'martin-to-ariella': MARTIN_TO_ARIELLA };

function usage(msg?: string): never {
  if (msg) console.error(`error: ${msg}\n`);
  console.error(`Usage:
  tes4 swap-scan <Oblivion.esm> --out <folder> [--voice <bsa>...] [--extract] [--preset martin-to-ariella]
      Find the character's record, dialogue, text and voice lines. Writes swap-plan.json,
      summary.md, recording-script.csv and pronoun-check.csv into the folder.
      The "Oblivion - Voices*.bsa" archives next to the .esm are checked automatically (or give --voice).
      --extract copies the original audio out: splice/ holds the files where someone else says the name
      (edit them in place, keep the folder layout), reference/ holds the character's own originals.
  tes4 swap-build <Oblivion.esm> <swap-plan.json> --out <Plugin.esp> [--accept-suggestions]
      Write a small .esp with the changed records. The .esm is not touched.`);
  process.exit(msg ? 2 : 0);
}

function option(args: string[], name: string): string | undefined {
  const i = args.indexOf(name);
  if (i < 0) return undefined;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
}

/** Every value of a repeatable option. */
function options(args: string[], name: string): string[] {
  const out: string[] = [];
  for (let v = option(args, name); v !== undefined; v = option(args, name)) out.push(v);
  return out;
}

function flag(args: string[], name: string): boolean {
  const i = args.indexOf(name);
  if (i < 0) return false;
  args.splice(i, 1);
  return true;
}

function load(path: string) {
  const b = readFileSync(path);
  return parseTes4(new Uint8Array(b.buffer, b.byteOffset, b.byteLength), path);
}

function main(argv: string[]): void {
  const [cmd, ...args] = argv;
  switch (cmd) {
    case undefined:
    case '-h':
    case '--help':
      return usage();
    case 'swap-scan': {
      const outDir = resolve(option(args, '--out') ?? usage('missing --out <folder>'));
      const presetName = option(args, '--preset') ?? 'martin-to-ariella';
      const preset = PRESETS[presetName as keyof typeof PRESETS] ?? usage(`unknown preset "${presetName}"`);
      const esm = args[0] ?? usage('missing the .esm path');
      const extract = flag(args, '--extract');
      console.error(`Reading ${esm}…`);
      const plan = scanSwap(load(esm), preset);
      const bsaPaths = options(args, '--voice');
      if (!bsaPaths.length) {
        const dir = dirname(resolve(esm));
        for (const f of readdirSync(dir)) if (/^oblivion - voices\d*\.bsa$/i.test(f)) bsaPaths.push(join(dir, f));
      }
      const archives = bsaPaths.map((p) => BsaArchive.open(p));
      if (archives.length) {
        console.error(`Checking ${archives.length} voice archive(s)…`);
        const index = indexVoice(archives);
        attachVoiceFiles(plan, index, bsaPaths.map((p) => basename(p)));
        if (extract) {
          let n = 0;
          for (const v of plan.voice) {
            for (const { entry, archive } of voiceEntries(v, index)) {
              // Lines others say go to splice/ (all folders); the character's own to reference/.
              const dest = join(outDir, v.kind === 'name' ? 'splice' : 'reference', ...entry.folder.split('\\'), entry.name);
              mkdirSync(dirname(dest), { recursive: true });
              writeFileSync(dest, archive.read(entry));
              n++;
            }
          }
          console.error(`Extracted ${n} original files.`);
        }
        archives.forEach((a) => a.close());
      } else if (extract) usage('--extract needs the voice archives (put them next to the .esm or pass --voice)');
      mkdirSync(outDir, { recursive: true });
      writeFileSync(join(outDir, 'swap-plan.json'), JSON.stringify(plan, null, 2));
      writeFileSync(join(outDir, 'summary.md'), planSummaryMarkdown(plan));
      writeFileSync(join(outDir, 'recording-script.csv'), recordingScriptCsv(plan));
      writeFileSync(join(outDir, 'pronoun-check.csv'), pronounCheckCsv(plan));
      console.log(planSummaryMarkdown(plan));
      console.log(`Wrote the plan to ${outDir}`);
      return;
    }
    case 'swap-build': {
      const out = resolve(option(args, '--out') ?? usage('missing --out <Plugin.esp>'));
      const accept = flag(args, '--accept-suggestions');
      const [esm, planPath] = args;
      if (!esm || !planPath) usage('need the .esm and the swap-plan.json');
      const plan = JSON.parse(readFileSync(planPath, 'utf8')) as SwapPlan;
      const res = buildSwapPlugin(load(esm), plan, { acceptSuggestions: accept });
      mkdirSync(dirname(out), { recursive: true });
      writeFileSync(out, res.plugin.write());
      console.log(`Wrote ${out}: ${res.written} text edits.`);
      for (const s of res.skipped) console.log(`  skipped ${s.id}: ${s.reason}`);
      for (const n of res.notes) console.log(`  note: ${n}`);
      return;
    }
    default:
      return usage(`unknown command "${cmd}"`);
  }
}

try {
  main(process.argv.slice(2));
} catch (e) {
  console.error(`error: ${(e as Error).message}`);
  process.exit(1);
}
