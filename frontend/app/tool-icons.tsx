'use client';
import {BookOpen, ChatCircleText, Lightbulb, Notebook, Exam, TreeStructure} from '@phosphor-icons/react';

/* Kept apart from tools.ts so the server route can read the tool data without
 * pulling the icon set — and React.createContext with it — into the server
 * component tree. */
const icons = {
  ask: ChatCircleText,
  guided: Lightbulb,
  notes: Notebook,
  'past-papers': BookOpen,
  practice: Exam,
  'study-map': TreeStructure,
} as const;

export default function ToolIcon({slug, size = 22, weight}: {slug: string; size?: number; weight?: 'duotone' | 'regular' | 'bold'}) {
  const Glyph = icons[slug as keyof typeof icons];
  return Glyph ? <Glyph size={size} weight={weight}/> : null;
}
