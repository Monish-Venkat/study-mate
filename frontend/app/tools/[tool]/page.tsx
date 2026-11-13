import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {bySlug, tools} from '../../tools';
import StudyTool from '../../study-tool';

export function generateStaticParams() {
  return tools.map(t => ({tool: t.slug}));
}

export async function generateMetadata({params}: {params: Promise<{tool: string}>}): Promise<Metadata> {
  const {tool} = await params;
  const def = bySlug(tool);
  return def ? {title: `${def.label} | StudyMate`, description: def.description}
             : {title: 'StudyMate'};
}

/* Only the slug crosses the server/client boundary: the tool definition holds
 * an icon component, which is not serialisable as a prop. */
export default async function ToolPage({params}: {params: Promise<{tool: string}>}) {
  const {tool} = await params;
  if (!bySlug(tool)) notFound();
  return <StudyTool slug={tool}/>;
}
