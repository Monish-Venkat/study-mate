/* Tool definitions — pure data, no imports.
 *
 * This module is read by the server component at app/tools/[tool]/page.tsx,
 * so it must stay free of anything client-only. Icons live in tool-icons.tsx
 * behind a 'use client' boundary: importing the icon set here dragged
 * React.createContext into the server tree and 500'd every route.
 *
 * `id` is what the API expects; `slug` is the URL. They differ because the
 * API ids are historical and the URLs should read well.
 */
export type Tool = {
  id: string;
  slug: string;
  label: string;
  title: string;
  description: string;
  action: string;
  blurb: string;
};

export const tools: Tool[] = [
  {
    id: 'ask', slug: 'ask', label: 'Ask a question',
    title: 'Make room for understanding.',
    description: 'Bring a question. Get an answer grounded in your own course material, with the passage behind every claim.',
    action: 'Ask StudyMate',
    blurb: 'An answer built from your textbook, structured as the value points the marking scheme rewards.',
  },
  {
    id: 'socratic', slug: 'guided', label: 'Guided learning',
    title: 'Find your way to the answer.',
    description: 'Work through a concept with guiding questions, one step at a time, instead of being handed the conclusion.',
    action: 'Start guided learning',
    blurb: 'Hints and questions that lead you to the result, for when the answer alone would not stick.',
  },
  {
    id: 'summary', slug: 'notes', label: 'Revision notes',
    title: 'The essentials, in focus.',
    description: 'Turn a chapter topic into a clear set of notes for your next revision pass.',
    action: 'Create revision notes',
    blurb: 'Definitions, formulas and the distinctions examiners test, drawn from the retrieved passages.',
  },
  {
    id: 'pyq', slug: 'past-papers', label: 'Past paper review',
    title: 'Learn from past questions.',
    description: 'Review the questions that recur across the available papers for your course.',
    action: 'Review past papers',
    blurb: 'Recurring topics and question forms across the board papers already in your index.',
  },
  {
    id: 'mock-paper', slug: 'practice', label: 'Practice paper',
    title: 'Put your knowledge to work.',
    description: 'Generate a practice paper from your course material, with marks and Bloom levels on every question.',
    action: 'Generate practice paper',
    blurb: 'A structured paper with mark allocation and internal choice, validated before you see it.',
  },
  {
    id: 'diagram', slug: 'study-map', label: 'Study map',
    title: 'See how the ideas connect.',
    description: 'Map a topic into its parts and the links between them — a revision aid for remembering structure, not a labelled exam diagram.',
    action: 'Draw the study map',
    blurb: 'How the ideas in a topic relate, so the structure is something you can recall under pressure.',
  },
];

export const bySlug = (slug: string) => tools.find(t => t.slug === slug);

export const subjects = ['physics', 'chemistry', 'mathematics', 'biology'] as const;

export const subjectBlurb: Record<string, string> = {
  physics: 'Derivations, ray diagrams and numericals with every step visible.',
  chemistry: 'Mechanisms, equations and the distinctions that carry marks.',
  mathematics: 'Worked solutions that show the method, not just the result.',
  biology: 'Processes, cycles and the labelled structures papers ask for.',
};
