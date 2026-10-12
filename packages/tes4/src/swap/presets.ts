import type { SwapPreset } from './types';

const GENDERED: SwapPreset['gendered'] = [
  { from: 'himself', to: 'herself' },
  { from: 'he', to: 'she' },
  { from: 'him', to: 'her' },
  { from: 'his', to: 'her' },
  { from: 'son', to: 'daughter' },
  { from: 'boy', to: 'girl' },
  { from: 'lad', to: 'lass' },
  { from: 'young man', to: 'young woman' },
  { from: 'Prince', to: 'Princess' },
];

/** Martin Septim (Oblivion.esm editor ID "Martin") becomes Ariella Septim. */
export const MARTIN_TO_ARIELLA: SwapPreset = {
  npcEditorId: 'Martin',
  npcNewName: 'Sister Ariella',
  setFemale: true,
  nameWord: 'Martin',
  names: [
    { from: '\\bBrother Martin\\b', to: 'Sister Ariella' },
    { from: '\\bMartin Septim\\b', to: 'Ariella Septim' },
    { from: '\\bMartin\\b', to: 'Ariella' },
  ],
  gendered: GENDERED,
};
