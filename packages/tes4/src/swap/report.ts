import type { SwapPlan, VoiceEntry } from './types';

const csvCell = (s: string | number) => `"${String(s).replace(/"/g, '""')}"`;

/** One row per audio file that needs new audio. Open in a spreadsheet or work down the Markdown list. */
export function recordingScriptCsv(plan: SwapPlan): string {
  const rows = [['#', 'task', 'file name', 'save in folder', 'new subtitle', 'original subtitle', 'quest', 'topic', 'notes']];
  sorted(plan.voice).forEach((v, i) =>
    rows.push([
      String(i + 1),
      v.kind === 'voice' ? 'record whole line' : 'splice the new name in',
      v.file + '.mp3',
      v.folder ?? 'same folder as the original file (found in the voice archives)',
      v.subtitle,
      v.originalSubtitle,
      v.quest,
      v.topic,
      v.notes,
    ]),
  );
  return rows.map((r) => r.map(csvCell).join(',')).join('\r\n') + '\r\n';
}

function sorted(v: VoiceEntry[]): VoiceEntry[] {
  return [...v].sort((a, b) => (a.kind === b.kind ? a.quest.localeCompare(b.quest) || a.infoId - b.infoId || a.response - b.response : a.kind === 'voice' ? -1 : 1));
}

export function planSummaryMarkdown(plan: SwapPlan): string {
  const voice = plan.voice.filter((v) => v.kind === 'voice');
  const names = plan.voice.filter((v) => v.kind === 'name');
  const review = plan.edits.filter((e) => e.status === 'review');
  const auto = plan.edits.filter((e) => e.status === 'auto');
  const lines: string[] = [];
  lines.push(`# Character swap: ${plan.npc.name || plan.npc.editorId} → ${plan.preset.npcNewName}`, '');
  lines.push(`Character: \`${plan.npc.editorId}\` (${plan.npc.formId.toString(16).toUpperCase().padStart(8, '0')}), race ${plan.npc.race}, currently ${plan.npc.female ? 'female' : 'male'}.`, '');
  lines.push('## What needs doing', '');
  lines.push(`- **${voice.length} spoken responses to record** in the new character's voice (the character's own lines). Save them in \`Sound\\Voice\\Oblivion.esm\\${plan.npc.race}\\${plan.preset.setFemale ? 'F' : 'M'}\\\`.`);
  lines.push(`- **${names.length} spoken responses where someone else says the name.** Splice the new name into the existing audio.`);
  lines.push(`- **${auto.length} subtitles** change by name only; written automatically.`);
  lines.push(`- **${review.length} subtitles** also contain gendered words (he, him, son...). Review them in \`swap-plan.json\`, or build with \`--accept-suggestions\`.`);
  lines.push(`- **${plan.pronounOnly.length} lines** in the character's quests talk about someone with a gendered word but no name. They may mean the character; they are listed in \`pronoun-check.csv\` and not changed.`);
  lines.push(`- **${plan.reportOnly.length} scripts** mention the name in their source (usually variable names). Nothing to do unless they print the name on screen.`, '');
  lines.push('## Needs the Construction Set', '');
  lines.push('- Lip-sync files (`.lip`) for every new audio file. The game plays new audio without them, but the mouth will not move.');
  if (plan.preset.setFemale && plan.npc.hasFaceData) lines.push('- The face. The character still has the original face data and needs a new face.');
  lines.push('');
  return lines.join('\n');
}

export function pronounCheckCsv(plan: SwapPlan): string {
  const rows = [['line id', 'quest', 'text']];
  for (const p of plan.pronounOnly) rows.push([p.editId, p.quest, p.text]);
  return rows.map((r) => r.map(csvCell).join(',')).join('\r\n') + '\r\n';
}
