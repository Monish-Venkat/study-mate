'use client';
import {useEffect, useRef, useState, type FormEvent} from 'react';
import Link from 'next/link';
import {BookOpen, ArrowRight, ArrowUpRight, Copy, DownloadSimple, Check, CircleNotch, WarningCircle, Trash} from '@phosphor-icons/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import SiteNav from './site-nav';
import PersonaPanel from './persona-panel';
import LearningPanel from './learning-panel';
import VoiceTools from './voice-tools';
import MockScore, {type Paper} from './mock-score';
import DiagramView from './diagram-view';
import GroundingBadge, {type Grounding} from './grounding-badge';
import FigureStrip from './figure-strip';
import PaperReport, {type Report} from './paper-report';
import BlueprintPreview from './blueprint-preview';
import {ToolDecor} from './decor-layers';
import {bySlug, subjects} from './tools';

type PersonaResult = {applied?: boolean; name?: string; reason?: string; sources?: {title: string; url: string; origin: string}[]};
type Diagram = {mermaid: string; notes: string; kind: string; abstained: boolean; message?: string; sources?: {source: string; page: string | number}[]};
type Result = {tool: string; title: string; answer: string; subject: string; level?: string; board?: string; paper?: Paper; persona?: PersonaResult; diagram?: Diagram; grounding?: Grounding; report?: Report};

const suggestions: Record<string, string[]> = {
  physics: ['Explain the principle of superposition.', 'How does an electric field differ from potential?', 'Derive the lens maker’s formula.'],
  chemistry: ['Explain chemical equilibrium.', 'How do ionic and covalent bonds differ?', 'Explain oxidation and reduction.'],
  mathematics: ['Explain derivatives with a simple example.', 'How do I solve a quadratic equation?', 'Help me understand probability.'],
  biology: ['Explain the stages of cell division.', 'How does photosynthesis work?', 'Explain Mendelian inheritance.'],
};

// The generator writes LaTeX with \[ \] and \( \) delimiters. remark-math only
// recognises $ and $$, so without this the backslashes survive to the page and
// a lens formula renders literally as "\[ \frac{1}{f} = (n-1)... \]".
// An odd number of delimiters is the damaging case: one stray $$ opens a block
// that runs to the end of the answer, so a single malformed formula rendered
// the rest of the text -- the closing sentence and the sources line -- as red
// raw LaTeX. Dropping the unmatched delimiter costs that one formula its
// formatting and leaves everything after it readable.
//
// Deterministic by construction: this runs in both the server render and the
// browser hydration of a Client Component, so it must produce the same string
// in each.
function dropUnmatched(text: string, delimiter: '$$' | '$'): string {
  let i = 0, count = 0, last = -1;
  while (i < text.length) {
    if (text[i] === '\\') { i += 2; continue; }      // \$ is an escaped dollar
    if (text.startsWith('$$', i)) {
      if (delimiter === '$$') { count++; last = i; }
      i += 2;
      continue;
    }
    if (text[i] === '$') {
      if (delimiter === '$') { count++; last = i; }
      i += 1;
      continue;
    }
    i += 1;
  }
  if (count % 2 === 0 || last < 0) return text;
  return text.slice(0, last) + text.slice(last + delimiter.length);
}

function toMath(text: string): string {
  const converted = text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_m, body: string) => `\n\n$$${body.trim()}$$\n\n`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_m, body: string) => `$${body.trim()}$`);
  return dropUnmatched(dropUnmatched(converted, '$$'), '$');
}

export default function StudyTool({slug}: {slug: string}) {
  const tool = bySlug(slug)!;
  const active = tool.id;

  const [subject, setSubject] = useState('physics');
  const [personaId, setPersonaId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [revision, setRevision] = useState(0);
  const [language, setLanguage] = useState('en');
  const [depth, setDepth] = useState('auto');
  const [level, setLevel] = useState('PUC2');
  const [board, setBoard] = useState('KA');
  const [question, setQuestion] = useState('');
  const [chapter, setChapter] = useState('');
  const [format, setFormat] = useState('bullet_points');
  const [marks, setMarks] = useState(70);
  const [topic, setTopic] = useState('');
  const [kind, setKind] = useState('concept_map');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [history, setHistory] = useState<Result[]>([]);
  const [copied, setCopied] = useState(false);
  const student = useRef('');
  const output = useRef<HTMLElement>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    let id = crypto.randomUUID() as string;
    try { id = localStorage.getItem('studymate-guest') || id; localStorage.setItem('studymate-guest', id); } catch {}
    student.current = id;
    setStudentId(id);
    // Subject arrives from the landing page's subject cards. Read it from the
    // URL directly rather than through useSearchParams, which would force the
    // whole route into a Suspense boundary for one optional value.
    const fromUrl = new URLSearchParams(window.location.search).get('subject');
    if (fromUrl && (subjects as readonly string[]).includes(fromUrl)) setSubject(fromUrl);
    return () => controller.current?.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setResult(null); setCopied(false);
    controller.current = new AbortController();
    const payload: Record<string, unknown> = {student_id: student.current, subject, level, board};
    if (active === 'ask' || active === 'socratic') { payload.question = question.trim(); payload.chapter = chapter.trim() || null; payload.language = language; payload.depth = depth; }
    if (['ask', 'socratic', 'summary'].includes(active)) payload.persona_id = personaId || null;
    if (active === 'summary') { payload.chapter = chapter.trim(); payload.summary_type = format; }
    if (active === 'mock-paper') payload.total_marks = marks;
    if (active === 'diagram') { payload.topic = topic.trim(); payload.chapter = chapter.trim() || null; payload.kind = kind; }
    try {
      const response = await fetch(`/api/study/${active}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), signal: controller.current.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check your inputs and try again.');
      const isDiagram = active === 'diagram';
      const answer = isDiagram ? (data.abstained ? (data.message || '') : (data.notes || '')) : (data.answer || data.summary || data.analysis || data.mock_paper);
      if (isDiagram) {
        if (!data.abstained && !data.mermaid) throw new Error('No study map was returned. Please try a narrower topic.');
      } else if (typeof answer !== 'string' || !answer.trim()) throw new Error('No answer was returned. Please try again.');
      const title = isDiagram ? (topic.trim() || tool.label)
        : question.trim() && (active === 'ask' || active === 'socratic') ? question.trim()
        : chapter.trim() && active === 'summary' ? chapter.trim() : tool.label;
      const entry = {tool: tool.label, title, answer, subject, level, board, paper: data.paper, persona: data.persona, grounding: data.grounding, diagram: isDiagram ? data as Diagram : undefined,
        // Past-paper review returns a structured report alongside the markdown
        // summary. The structure is what distinguishes board-paper evidence
        // from question-bank volume, so it is rendered rather than the prose.
        report: data.report as Report | undefined};
      setRevision(v => v + 1);
      setResult(entry);
      setHistory(previous => [entry, ...previous].slice(0, 8));
      setTimeout(() => output.current?.scrollIntoView({behavior: 'smooth', block: 'start'}), 50);
    } catch (e) {
      if (!(e instanceof DOMException && e.name === 'AbortError')) setError(e instanceof Error ? e.message : 'Something went wrong. Please retry.');
    } finally { setBusy(false); }
  }

  async function copy() {
    try { await navigator.clipboard.writeText(result!.answer); setCopied(true); }
    catch { setError('Copy is unavailable in this browser. Use Download notes instead.'); }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([result!.answer], {type: 'text/plain;charset=utf-8'}));
    const a = document.createElement('a');
    a.href = url; a.download = `studymate-${subject}.txt`; a.click();
    URL.revokeObjectURL(url);
  }

  return <>
    <SiteNav/>
    <a href="#study-form" className="skip-link">Skip to study tool</a>
    <div className="decor-field">
    <ToolDecor slug={slug} subject={subject}/>
    <main className="tool-page">
      <p className="tool-breadcrumb"><Link href="/">StudyMate</Link> / {tool.label}</p>
      <div className="tool-head">
        <span className="subject-pill" data-subject={subject}>{subject[0].toUpperCase() + subject.slice(1)} · {level === 'PUC1' ? '1st PUC' : '2nd PUC'}</span>
        <h1>{tool.title}</h1>
        <p>{tool.description}</p>
      </div>

      <form id="study-form" onSubmit={submit}>
        <fieldset disabled={busy}>
          <legend>Your course</legend>
          <div className="course-fields">
            <label>Subject<select value={subject} onChange={e => {setSubject(e.target.value); setPersonaId(''); setResult(null);}}>{subjects.map(s => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}</select></label>
            <label>Year<select value={level} onChange={e => {setLevel(e.target.value); setResult(null);}}><option value="PUC1">1st PUC</option><option value="PUC2">2nd PUC</option></select></label>
            <label>Board<select value={board} onChange={e => {setBoard(e.target.value); setResult(null);}}><option value="KA">Karnataka</option><option value="CBSE">CBSE</option></select></label>
          </div>
          {board === 'CBSE' && <p className="inline-note">The supplied papers are for Karnataka. CBSE requests may have no matching sources.</p>}
          <div className="form-divider"/>

          {(active === 'ask' || active === 'socratic') && <div className="learning-preferences">
            <label>Response language<select value={language} onChange={e => setLanguage(e.target.value)}>{[['en', 'English'], ['hi', 'Hindi'], ['kn', 'Kannada'], ['ta', 'Tamil'], ['te', 'Telugu'], ['ml', 'Malayalam'], ['mr', 'Marathi'], ['bn', 'Bengali']].map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
            <label>Teaching approach<select value={depth} onChange={e => setDepth(e.target.value)}>{[['auto', 'Adapt to my progress'], ['concise', 'Concise'], ['step_by_step', 'Step by step'], ['analogy', 'Analogy'], ['worked_example', 'Worked example'], ['socratic', 'Guiding questions']].map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
          </div>}

          {(active === 'ask' || active === 'socratic') && <label className="question-label">What would you like to understand?<textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="For example, why do two waves sometimes cancel each other out?" required maxLength={4000} rows={5}/></label>}

          {(active === 'ask' || active === 'socratic' || active === 'summary' || active === 'diagram') && <label className="chapter-label">{active === 'summary' ? 'Chapter or topic' : 'Chapter or topic (optional)'}<input value={chapter} onChange={e => setChapter(e.target.value)} placeholder="e.g. Wave optics" required={active === 'summary'} maxLength={200}/></label>}

          {active === 'summary' && <label className="extra-field">Notes format<select value={format} onChange={e => setFormat(e.target.value)}><option value="bullet_points">Bullet points</option><option value="detailed">Detailed explanation</option><option value="quick_revision">Quick revision</option></select></label>}

          {active === 'mock-paper' && <>
            <label className="extra-field">Total marks<input type="number" min={10} max={200} required value={marks} onChange={e => setMarks(Number(e.target.value))}/></label>
            <BlueprintPreview totalMarks={marks}/>
            <p className="inline-note">Question structure, marks totals and internal choices are validated before delivery. Review academic quality before formal assessment.</p>
          </>}

          {active === 'diagram' && <>
            <label className="question-label">Which topic should the study map show?<input value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. Refraction of light through a prism" required maxLength={200}/></label>
            <label className="extra-field">Map type<select value={kind} onChange={e => setKind(e.target.value)}><option value="concept_map">Concept map &mdash; how the ideas relate</option><option value="process">Process flow &mdash; the stages in order</option><option value="derivation">Derivation chain &mdash; premises to result</option><option value="comparison">Comparison &mdash; two concepts side by side</option><option value="classification">Classification tree &mdash; types and sub-types</option></select></label>
            <p className="inline-note">A study map shows how ideas connect, for revision. It is not the labelled diagram a board paper awards marks for &mdash; draw that from your textbook.</p>
          </>}

          {active === 'pyq' && <p className="inline-note">Questions are read from the board papers and question banks in your index and grouped by meaning, so differently worded questions about one concept count together. Recurrence is taken from board papers only; papers whose text cannot be extracted are listed rather than silently dropped.</p>}

          <div className="form-footer">
            <span>Answers grounded in retrieved material</span>
            <button className="primary-button" type="submit">{busy ? <><CircleNotch className="spinner" size={18}/>Working on it…</> : <>{tool.action}<ArrowRight size={17}/></>}</button>
          </div>
        </fieldset>
      </form>

      {(active === 'ask' || active === 'socratic') && <VoiceTools key={`${subject}-${level}-${board}`} language={language} answer={result?.answer} onTranscript={(text, detected) => {setQuestion(text); if (['en', 'hi', 'kn', 'ta', 'te', 'ml', 'mr', 'bn'].includes(detected)) setLanguage(detected);}}/>}

      {busy && <div className="loading-state" role="status"><p>Looking through your course material and preparing a response. Local models can take a moment.</p><button className="text-button" onClick={() => controller.current?.abort()}>Cancel request</button></div>}

      {error && <div role="alert" className="error-state"><WarningCircle size={21}/><div><strong>We couldn&rsquo;t complete that request.</strong><p>{error}</p><button className="text-button" onClick={() => {setError(''); document.getElementById('study-form')?.scrollIntoView();}}>Back to request</button></div></div>}

      {result && <section className="answer-panel" ref={output} aria-label="Study response" aria-live="polite">
        <header>
          <div><span className="answer-subject">{result.subject} / {result.tool}</span><h2>{result.title}</h2></div>
          <div className="answer-actions">
            <button onClick={copy} aria-label={copied ? 'Copied' : 'Copy answer'} title="Copy answer">{copied ? <Check size={19}/> : <Copy size={19}/>}</button>
            <button onClick={download} aria-label="Download notes" title="Download notes"><DownloadSimple size={19}/></button>
          </div>
        </header>
        <div className="persona-result">
          {result.persona?.reason && <p>{result.persona.applied ? `${result.persona.name}: ` : ''}{result.persona.reason}</p>}
          {result.persona?.sources && <details><summary>Teaching-style references (not factual sources)</summary>{result.persona.sources.map((source, i) => <p key={i}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>{source.origin === 'pasted' ? ' · User-supplied transcript' : ' · YouTube captions'}</p>)}</details>}
        </div>
        {result.diagram && !result.diagram.abstained && <DiagramView code={result.diagram.mermaid} title={result.title}/>}
        {active === 'pyq' && result.report
          ? <PaperReport report={result.report}/>
          : <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{toMath(result.answer)}</ReactMarkdown></div>}
        {result.diagram && !result.diagram.abstained && (result.diagram.sources?.length ?? 0) > 0 && <details className="diagram-sources"><summary>Drawn from {result.diagram.sources!.length} retrieved passage{result.diagram.sources!.length === 1 ? '' : 's'}</summary><ul>{result.diagram.sources!.map((src, i) => <li key={i}>[{i + 1}] {src.source} &middot; page {src.page}</li>)}</ul></details>}
        {['ask', 'socratic', 'summary', 'diagram'].includes(active) &&
          <FigureStrip query={result.title} subject={result.subject} level={result.level || level}/>}
        <GroundingBadge grounding={result.grounding}/>
        {result.paper && <MockScore key={result.paper.id} paper={result.paper} studentId={studentId} subject={result.subject} level={result.level || level} board={result.board || board} onSaved={() => setRevision(v => v + 1)}/>}
        <p className="answer-footnote">Use the source references to check the explanation against your textbook.</p>
      </section>}

      {!result && !busy && (active === 'ask' || active === 'socratic') && <section className="starters">
        <h2>A starting point, if you need one</h2>
        <p>Questions drawn from the {subject} material already in your index.</p>
        <div className="starter-grid">
          {suggestions[subject].map(s => <button key={s} type="button" className="starter-card" data-subject={subject}
            onClick={() => {setQuestion(s); document.querySelector<HTMLTextAreaElement>('textarea')?.focus();}}>
            <b>{s}</b>
            <footer>{subject[0].toUpperCase() + subject.slice(1)}<ArrowUpRight size={14}/></footer>
          </button>)}
        </div>
      </section>}

      {!result && !busy && <section className="how">
        <h2>How your answer is built</h2>
        <div className="how-steps">
          <div className="how-step">
            <span>1</span>
            <b>Retrieved</b>
            <p>Passages are filtered to your subject, year and board before ranking, then found by meaning and by exact term together.</p>
          </div>
          <div className="how-step">
            <span>2</span>
            <b>Grounded</b>
            <p>Answers are written only from those passages. When the material does not cover your question, StudyMate says so instead of filling the gap from memory.</p>
          </div>
          <div className="how-step">
            <span>3</span>
            <b>Audited</b>
            <p>The finished answer is read back against its evidence, and any claim that cannot be traced is flagged beside it.</p>
          </div>
        </div>
      </section>}

      {['ask', 'socratic', 'summary'].includes(active) && <details className="secondary-panel">
        <summary>Teaching style <small>— answer in the manner of a registered educator</small></summary>
        <PersonaPanel subject={subject} selected={personaId} onSelect={setPersonaId} disabled={busy}/>
      </details>}

      {history.length > 1 && <section className="recent">
        <div className="status-heading"><h2>This session</h2><button aria-label="Clear session results" title="Clear session results" onClick={() => {setHistory([]); setResult(null);}}><Trash size={16}/></button></div>
        {history.map((entry, i) => <button key={i} disabled={busy} onClick={() => {setResult(entry); setCopied(false);}}><span>{entry.title}</span><small>{entry.tool}</small></button>)}
      </section>}

      {active === 'mock-paper' && <LearningPanel studentId={studentId} subject={subject} level={level} board={board} revision={revision} onClear={() => {const id = crypto.randomUUID(); student.current = id; setStudentId(id); try {localStorage.setItem('studymate-guest', id);} catch {} setHistory([]); setResult(null);}}/>}
    </main>

    <footer className="tool-footer">
      <span><BookOpen size={14} style={{verticalAlign: '-2px', marginRight: 6}}/>Your material. Your pace.</span>
      <span>Check important answers against your course material.</span>
    </footer>
    </div>
  </>;
}
