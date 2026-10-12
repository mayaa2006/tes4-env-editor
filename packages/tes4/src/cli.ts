#!/usr/bin/env node
/**
 * tes4 — Oblivion plugin tools.
 *
 *   tes4 swap-scan  <Oblivion.esm> --out <folder> [--preset martin-to-ariella]
 *   tes4 swap-build <Oblivion.esm> <swap-plan.json> --out <Plugin.esp> [--accept-suggestions]
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { MARTIN_TO_ARIELLA, buildSwapPlugin, parseTes4, planSummaryMarkdown, pronounCheckCsv, recordingScriptCsv, scanSwap, type SwapPlan } from './index';

const PRESETS = { 'martin-to-ariella': MARTIN_TO_ARIELLA };

function usage(msg?: string): never {
  if (msg) console.error(`error: ${msg}\n`);
  console.error(`Usage:
  tes4 swap-scan <Oblivion.esm> --out <folder> [--preset martin-to-ariella]
      Find the character's record, dialogue, text and voice lines. Writes swap-plan.json,
      summary.md, recording-script.csv and pronoun-check.csv into the folder.
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
      console.error(`Reading ${esm}…`);
      const plan = scanSwap(load(esm), preset);
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
