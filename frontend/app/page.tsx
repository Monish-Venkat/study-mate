"use client";
import {useEffect, useRef, useState, type FormEvent} from 'react';
import {BookOpen, ChatCircleText, Lightbulb, Notebook, Exam, TreeStructure, Sun, Moon, ArrowRight, ArrowUpRight, ArrowClockwise, Copy, DownloadSimple, Check, CircleNotch, WarningCircle, Trash, YoutubeLogo} from '@phosphor-icons/react';
import PersonaPanel from './persona-panel';
import LearningPanel from './learning-panel';
import VoiceTools from './voice-tools';
import MockScore,{type Paper} from './mock-score';
import DiagramView from './diagram-view';
import GroundingBadge,{type Grounding} from './grounding-badge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const tools = [
  {id:'ask', label:'Ask a question', icon:ChatCircleText, title:'Make room for understanding.', description:'Bring a question. Explore an answer grounded in your course material.', action:'Ask StudyMate'},
  {id:'socratic', label:'Guided learning', icon:Lightbulb, title:'Find your way to the answer.', description:'Work through a concept with guiding questions, one step at a time.', action:'Start guided learning'},
  {id:'summary', label:'Revision notes', icon:Notebook, title:'The essentials, in focus.', description:'Turn a chapter topic into a clear set of notes for your next revision.', action:'Create revision notes'},
  {id:'pyq', label:'Past paper review', icon:BookOpen, title:'Learn from past questions.', description:'Explore questions from the available papers for your selected course.', action:'Review past papers'},
  {id:'mock-paper', label:'Practice paper', icon:Exam, title:'Put your knowledge to work.', description:'Create a practice paper from your course material, with marks and Bloom levels.', action:'Generate practice paper'},
  {id:'diagram', label:'Concept diagram', icon:TreeStructure, title:'See how the ideas connect.', description:'Turn a topic into a diagram drawn only from your course material.', action:'Draw the diagram'},
] as const;
type ToolId = typeof tools[number]['id'];
type PersonaResult = {applied?:boolean;name?:string;reason?:string;sources?:{title:string;url:string;origin:string}[]};
type Diagram = {mermaid:string;notes:string;kind:string;abstained:boolean;message?:string;sources?:{source:string;page:string|number}[]};
type Result = {tool:string; title:string; answer:string; subject:string;level?:string;board?:string;paper?:Paper;persona?:PersonaResult;diagram?:Diagram;grounding?:Grounding};
const subjects = ['physics','chemistry','mathematics','biology'];
const suggestions: Record<string,string[]> = {
  physics:['Explain the principle of superposition.','How does an electric field differ from potential?','Help me understand the laws of motion.'],
  chemistry:['Explain chemical equilibrium.','How do ionic and covalent bonds differ?','Explain oxidation and reduction.'],
  mathematics:['Explain derivatives with a simple example.','How do I solve a quadratic equation?','Help me understand probability.'],
  biology:['Explain the stages of cell division.','How does photosynthesis work?','Explain Mendelian inheritance.'],
};
export default function Home() {
  const [active,setActive] = useState<ToolId>('ask');
  const [subject,setSubject] = useState('physics');
  const [personaId,setPersonaId] = useState('');
  const [studentId,setStudentId] = useState('');
  const [revision,setRevision] = useState(0);
  const [language,setLanguage] = useState('en');
  const [depth,setDepth] = useState('auto');
  const [level,setLevel] = useState('PUC2');
  const [board,setBoard] = useState('KA');
  const [question,setQuestion] = useState('');
  const [chapter,setChapter] = useState('');
  const [format,setFormat] = useState('bullet_points');
  const [marks,setMarks] = useState(70);
  const [topic,setTopic] = useState('');
  const [kind,setKind] = useState('concept_map');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [health,setHealth] = useState<'checking'|'offline'|'empty'|'ready'>('checking');
  const [result,setResult] = useState<Result|null>(null);
  const [history,setHistory] = useState<Result[]>([]);
  const [copied,setCopied] = useState(false);
  const [theme,setTheme] = useState<'light'|'dark'|null>(null);
  const student = useRef('');
  const output = useRef<HTMLElement>(null);
  const controller = useRef<AbortController|null>(null);
  const tool = tools.find(t=>t.id===active)!;
  async function checkHealth() {
    setHealth('checking');
    try { const res = await fetch('/api/study/health'); const data = await res.json(); setHealth(!res.ok?'offline':data.index_ready?'ready':'empty'); }
    catch {setHealth('offline');}
  }
  useEffect(()=>{
    let id=crypto.randomUUID() as string;
    try {id=localStorage.getItem('studymate-guest')||id;localStorage.setItem('studymate-guest',id);} catch {}
    student.current=id;setStudentId(id);
    const stored=document.documentElement.dataset.theme as 'light'|'dark'|undefined;
    setTheme(stored||(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
    checkHealth();
    return ()=>controller.current?.abort();
  },[]);
  function changeTool(id:ToolId) {setActive(id);setError('');setResult(null);}
  function toggleTheme() {
    const next = theme==='dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {localStorage.setItem('studymate-theme',next);} catch {}
  }
  async function submit(event:FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);setError('');setResult(null);setCopied(false);
    controller.current = new AbortController();
    const payload: Record<string,unknown> = {student_id:student.current,subject,level,board};
    if (active==='ask'||active==='socratic') {payload.question=question.trim();payload.chapter=chapter.trim()||null;payload.language=language;payload.depth=depth;}
    if (['ask','socratic','summary'].includes(active)) payload.persona_id=personaId||null;
    if (active==='summary') {payload.chapter=chapter.trim();payload.summary_type=format;}
    if (active==='mock-paper') payload.total_marks=marks;
    if (active==='diagram') {payload.topic=topic.trim();payload.chapter=chapter.trim()||null;payload.kind=kind;}
    try {
      const response = await fetch(`/api/study/${active}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.current.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Please check your inputs and try again.');
      // A diagram answers with mermaid source plus a reading guide, so the
      // emptiness check has to look at the diagram, not at prose.
      const isDiagram = active==='diagram';
      const answer = isDiagram ? (data.abstained ? (data.message||'') : (data.notes||'')) : (data.answer||data.summary||data.analysis||data.mock_paper);
      if (isDiagram) {
        if (!data.abstained && !data.mermaid) throw new Error('No diagram was returned. Please try a narrower topic.');
      } else if (typeof answer!=='string'||!answer.trim()) throw new Error('No answer was returned. Please try again.');
      const title = isDiagram ? (topic.trim()||tool.label)
        : question.trim()&&(active==='ask'||active==='socratic') ? question.trim()
        : chapter.trim()&&active==='summary' ? chapter.trim() : tool.label;
      const entry = {tool:tool.label,title,answer,subject,level,board,paper:data.paper,persona:data.persona,grounding:data.grounding,diagram:isDiagram?data as Diagram:undefined};
      setRevision(v=>v+1);setResult(entry);setHistory(previous=>[entry,...previous].slice(0,8));
      setTimeout(()=>output.current?.scrollIntoView({behavior:'smooth',block:'start'}),50);
    } catch (e) {if (!(e instanceof DOMException&&e.name==='AbortError')) setError(e instanceof Error?e.message:'Something went wrong. Please retry.');}
    finally {setBusy(false);}
  }
  async function copy() {try {await navigator.clipboard.writeText(result!.answer);setCopied(true);} catch {setError('Copy is unavailable in this browser. Use Download notes instead.');}}
  function download() {const url=URL.createObjectURL(new Blob([result!.answer],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`studymate-${subject}.txt`;a.click();URL.revokeObjectURL(url);}
  return <div className="workspace">
    <a href="#study-form" className="skip-link">Skip to study tool</a>
    <aside className="sidebar">
      <a href="/" className="brand"><BookOpen weight="duotone" size={30}/><span>StudyMate<span className="brand-caption">A little clarity, every day.</span></span></a>
      <nav aria-label="Study tools">{tools.map(item=><button key={item.id} aria-current={active===item.id?'page':undefined} disabled={busy} className={active===item.id?'nav-item selected':'nav-item'} onClick={()=>changeTool(item.id)}><item.icon size={21}/><span>{item.label}</span>{active===item.id&&<ArrowRight size={16}/>}</button>)}<button className="nav-item" type="button" onClick={()=>document.getElementById("persona-heading")?.scrollIntoView({behavior:"smooth",block:"start"})}><YoutubeLogo size={21}/><span>YouTube persona</span></button><button className="nav-item" onClick={()=>document.getElementById("learning-plan")?.scrollIntoView({behavior:"smooth"})}><Notebook size={21}/><span>Study plan & scores</span></button><a className="nav-item" href="/teacher"><Exam size={21}/><span>Teacher tools</span></a></nav>
      <div className="sidebar-note"><BookOpen size={25}/><h3>Your material. Your pace.</h3><p>Study with your PUC textbooks and available question papers.</p></div>
      <div className="session"><span>Guest workspace</span><small>No account needed</small></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><span>My study workspace</span><span className="course-tag">PUC learning companion</span><button type="button" className="theme-toggle" onClick={toggleTheme} title={theme==='dark'?'Switch to light theme':'Switch to dark theme'} aria-label={theme==='dark'?'Switch to light theme':'Switch to dark theme'}>{theme==='dark'?<Sun size={18}/>:<Moon size={18}/>}</button></header>
      <main>
        <div className="page-heading"><h1>{tool.title}</h1><p>{tool.description}</p></div>
        <div className="study-layout">
          <div className="primary-column">
            <PersonaPanel subject={subject} selected={personaId} onSelect={setPersonaId} disabled={busy}/>
            <form id="study-form" onSubmit={submit}>
              <fieldset disabled={busy}>
                <legend>Your course</legend>
                <div className="course-fields">
                  <label>Subject<select value={subject} onChange={e=>{setSubject(e.target.value);setPersonaId('');setResult(null);}}>{subjects.map(s=><option key={s} value={s}>{s[0].toUpperCase()+s.slice(1)}</option>)}</select></label>
                  <label>Year<select value={level} onChange={e=>{setLevel(e.target.value);setResult(null);}}><option value="PUC1">1st PUC</option><option value="PUC2">2nd PUC</option></select></label>
                  <label>Board<select value={board} onChange={e=>{setBoard(e.target.value);setResult(null);}}><option value="KA">Karnataka</option><option value="CBSE">CBSE</option></select></label>
                </div>
                {board==='CBSE'&&<p className="inline-note">The supplied papers are for Karnataka. CBSE requests may have no matching sources.</p>}
                <div className="form-divider"/>
                {(active==='ask'||active==='socratic')&&<div className="persona-fields learning-preferences"><label>Response language<select value={language} onChange={e=>setLanguage(e.target.value)}>{[['en','English'],['hi','Hindi'],['kn','Kannada'],['ta','Tamil'],['te','Telugu'],['ml','Malayalam'],['mr','Marathi'],['bn','Bengali']].map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label><label>Teaching approach<select value={depth} onChange={e=>setDepth(e.target.value)}>{[['auto','Adapt to my progress'],['concise','Concise'],['step_by_step','Step by step'],['analogy','Analogy'],['worked_example','Worked example'],['socratic','Guiding questions']].map(([code,name])=><option key={code} value={code}>{name}</option>)}</select></label></div>}
                {(active==='ask'||active==='socratic')&&<label className="question-label">What would you like to understand?<textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="For example, why do two waves sometimes cancel each other out?" required maxLength={4000} rows={5}/></label>}
                {(active==='ask'||active==='socratic'||active==='summary'||active==='diagram')&&<label className="chapter-label">{active==='summary'?'Chapter or topic':'Chapter or topic (optional)'}<input value={chapter} onChange={e=>setChapter(e.target.value)} placeholder="e.g. Wave optics" required={active==='summary'} maxLength={200}/></label>}
                {active==='summary'&&<label className="extra-field">Notes format<select value={format} onChange={e=>setFormat(e.target.value)}><option value="bullet_points">Bullet points</option><option value="detailed">Detailed explanation</option><option value="quick_revision">Quick revision</option></select></label>}
                {active==='mock-paper'&&<><label className="extra-field">Total marks<input type="number" min={10} max={200} required value={marks} onChange={e=>setMarks(Number(e.target.value))}/></label><p className="inline-note">Question structure, marks totals and internal choices are validated before delivery. Review academic quality before formal assessment.</p></>}
                {active==='diagram'&&<><label className="question-label">Which topic should the diagram show?<input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="e.g. Refraction of light through a prism" required maxLength={200}/></label><label className="extra-field">Diagram type<select value={kind} onChange={e=>setKind(e.target.value)}><option value="concept_map">Concept map &mdash; how the ideas relate</option><option value="process">Process flow &mdash; the stages in order</option><option value="derivation">Derivation chain &mdash; premises to result</option><option value="comparison">Comparison &mdash; two concepts side by side</option><option value="classification">Classification tree &mdash; types and sub-types</option></select></label><p className="inline-note">Every node is drawn from retrieved passages. If the material is too thin to connect, StudyMate says so instead of inventing a structure.</p></>}{active==='pyq'&&<div className="tool-description"><BookOpen size={34}/><h2>A closer look at past papers</h2><p>Calculate topic frequencies, TF-IDF keywords and mark distributions across the available five-year archive. Missing years and unreviewed extraction are reported.</p></div>}
                <div className="form-footer"><span>Answers grounded in retrieved material</span><button className="primary-button" type="submit">{busy?<><CircleNotch className="spinner" size={19}/>Working on it...</>:<>{tool.action}<ArrowRight size={18}/></>}</button></div>
              </fieldset>
            </form>
            {(active==='ask'||active==='socratic')&&<VoiceTools key={`${subject}-${level}-${board}`} language={language} answer={result?.answer} onTranscript={(text,detected)=>{setQuestion(text);if(['en','hi','kn','ta','te','ml','mr','bn'].includes(detected))setLanguage(detected);}}/>}
            {busy&&<div className="loading-state" role="status"><p>Looking through your course material and preparing a response. Local models can take a moment.</p><button className="text-button" onClick={()=>controller.current?.abort()}>Cancel request</button></div>}
            {error&&<div role="alert" className="error-state"><WarningCircle size={22}/><div><strong>We couldn’t complete that request.</strong><p>{error}</p><button className="text-button" onClick={()=>{setError('');document.getElementById('study-form')?.scrollIntoView();}}>Back to request</button></div></div>}
            {result&&<section className="answer-panel" ref={output} aria-label="Study response" aria-live="polite"><header><div><span className="answer-subject">{result.subject} / {result.tool}</span><h2>{result.title}</h2></div><div className="answer-actions"><button onClick={copy} aria-label={copied?'Copied':'Copy answer'} title="Copy answer">{copied?<Check size={20}/>:<Copy size={20}/>}</button><button onClick={download} aria-label="Download notes" title="Download notes"><DownloadSimple size={20}/></button></div></header><div className="persona-result">{result.persona?.reason&&<p>{result.persona.applied?`${result.persona.name}: `:""}{result.persona.reason}</p>}{result.persona?.sources&&<details><summary>Teaching-style references (not factual sources)</summary>{result.persona.sources.map((source,i)=><p key={i}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>{source.origin==='pasted'?' · User-supplied transcript':' · YouTube captions'}</p>)}</details>}</div>{result.diagram&&!result.diagram.abstained&&<DiagramView code={result.diagram.mermaid} title={result.title}/>}<div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{result.answer}</ReactMarkdown></div>{result.diagram&&!result.diagram.abstained&&(result.diagram.sources?.length??0)>0&&<details className="diagram-sources"><summary>Drawn from {result.diagram.sources!.length} retrieved passage{result.diagram.sources!.length===1?"":"s"}</summary><ul>{result.diagram.sources!.map((src,i)=><li key={i}>[{i+1}] {src.source} &middot; page {src.page}</li>)}</ul></details>}<GroundingBadge grounding={result.grounding}/>{result.paper&&<MockScore key={result.paper.id} paper={result.paper} studentId={studentId} subject={result.subject} level={result.level||level} board={result.board||board} onSaved={()=>setRevision(v=>v+1)}/>}<p className="answer-footnote">Use the source references to check the explanation against your textbook.</p></section>}
            {!result&&!busy&&(active==='ask'||active==='socratic')&&<section className="suggestions"><h2>A starting point, if you need one</h2>{suggestions[subject].map(s=><button key={s} onClick={()=>{setQuestion(s);document.querySelector<HTMLTextAreaElement>('textarea')?.focus();}}>{s}<ArrowUpRight size={18}/></button>)}</section>}
            <LearningPanel studentId={studentId} subject={subject} level={level} board={board} revision={revision} onClear={()=>{const id=crypto.randomUUID();student.current=id;setStudentId(id);try{localStorage.setItem('studymate-guest',id);}catch{}setHistory([]);setResult(null);}}/>
          </div>
          <aside className="study-aside">
            <section className="study-note"><div className="note-icon"><Lightbulb size={26} weight="duotone"/></div><h2>Understanding starts<br/>with a good question.</h2><p>Tell StudyMate what you already know and exactly where you get stuck.</p><div className="example"><span>Try being specific</span><p>“I understand wavelength, but how does it affect interference?”</p></div></section>
            <section className="service-status"><div className="status-heading"><h2>Study service</h2><button onClick={checkHealth} aria-label="Refresh service status" title="Refresh status"><ArrowClockwise size={17}/></button></div><p role="status">{health==='checking'?'Checking connection...':health==='offline'?'Backend is offline':health==='empty'?'Course index is empty':'Course index is ready'}</p><small>{health==='offline'?'Start the backend, then refresh.':health==='empty'?'Run the index builder before studying.':health==='ready'?'Answers also require a running Ollama model.':'Connecting to your local workspace.'}</small></section>
            {history.length>0&&<section className="recent"><div className="status-heading"><h2>This session</h2><button aria-label="Clear session results" title="Clear session results" onClick={()=>{setHistory([]);setResult(null);}}><Trash size={17}/></button></div>{history.map((entry,i)=><button key={i} disabled={busy} onClick={()=>{setResult(entry);setCopied(false);}}><span>{entry.title}</span><small>{entry.tool}</small></button>)}</section>}
          </aside>
        </div>
        <footer className="page-footer"><span>Made for focused study.</span><span>Check important answers against your course material.</span></footer>
      </main>
    </div>
  </div>;
}
