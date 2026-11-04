"use client";
import {useCallback,useEffect,useState,type FormEvent} from 'react';
import {YoutubeLogo,ArrowClockwise,CircleNotch} from '@phosphor-icons/react';
export type Educator={id:string;name:string;subject:string;ready:boolean;passage_count:number;descriptor:Record<string,string>|null;videos:{id:string;title:string;url:string;status:string;error:string|null;passage_count:number;origin:string}[]};
export default function PersonaPanel({subject,selected,onSelect,disabled}:{subject:string;selected:string;onSelect:(id:string)=>void;disabled:boolean}) {
  const [educators,setEducators]=useState<Educator[]>([]);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [name,setName]=useState('');
  const [url,setUrl]=useState('');
  const [title,setTitle]=useState('');
  const [language,setLanguage]=useState('en');
  const [transcript,setTranscript]=useState('');
  const [existing,setExisting]=useState('');
  const [manual,setManual]=useState(false);
  const refresh=useCallback(async()=>{
    try {const response=await fetch('/api/personas');const data=await response.json();if(!response.ok)throw new Error(data.detail);setEducators(data.educators);setError('');}
    catch(e){setError(e instanceof Error?e.message:'Unable to load educators.');}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{refresh();},[refresh]);
  const processing=educators.some(e=>e.videos.some(v=>v.status==='processing'));
  useEffect(()=>{if(!processing)return;const timer=setInterval(refresh,4000);return()=>clearInterval(timer);},[processing,refresh]);
  useEffect(()=>{setExisting('');setNotice('');},[subject]);
  const available=educators.filter(e=>e.subject===subject);
  async function register(event:FormEvent) {
    event.preventDefault();setSaving(true);setError('');setNotice('');
    try {
      const response=await fetch('/api/personas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:existing?educators.find(e=>e.id===existing)?.name:name.trim(),educator_id:existing||null,subject,url:url.trim(),title:title.trim(),language,transcript:manual?transcript.trim():null})});
      const data=await response.json();if(!response.ok)throw new Error(data.detail||'Registration failed.');
      setNotice(data.queued?'Import started. You can keep studying while captions and the style profile are prepared.':'This video is already registered. See its status below.');
      setTranscript('');await refresh();
    } catch(e){setError(e instanceof Error?e.message:'Registration failed.');}
    finally{setSaving(false);}
  }
  return <section className="persona-panel" aria-labelledby="persona-heading">
    <div className="persona-heading"><div><YoutubeLogo size={25}/><h2 id="persona-heading">YouTube teaching persona</h2></div><button type="button" aria-label="Refresh educators" onClick={refresh}><ArrowClockwise size={19}/></button></div>
    <p>Bring a familiar teaching style to your questions, guided learning and revision. Answers still use your course material.</p>
    <label>Teaching style<select disabled={disabled||loading} value={selected} onChange={e=>onSelect(e.target.value)}><option value="">Standard StudyMate</option>{available.map(e=><option key={e.id} value={e.id} disabled={!e.ready}>{e.name}{!e.ready?' (not ready)':''}</option>)}</select></label>
    {loading&&<p role="status">Loading educators...</p>}
    {!loading&&available.length===0&&!error&&<p className="inline-note">No educators for {subject} yet. Add your first lecture below.</p>}
    {selected&&<p className="inline-note">Style is used only when five relevant transcript passages match your question. Otherwise, you receive a standard explanation.</p>}
    <details className="persona-register"><summary>Add a YouTube lecture</summary>
      <form onSubmit={register} className="persona-form"><fieldset disabled={saving}>
        <label>Educator profile<select value={existing} onChange={e=>setExisting(e.target.value)}><option value="">Create an educator</option>{available.map(e=><option key={e.id} value={e.id}>{e.name}</option>)}</select></label>
        {!existing&&<label>Educator name<input required maxLength={100} value={name} onChange={e=>setName(e.target.value)} placeholder="Name of the lecturer or channel"/></label>}
        <label>YouTube video URL<input required type="url" maxLength={500} value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..."/></label>
        <div className="persona-fields"><label>Lecture title (optional)<input maxLength={200} value={title} onChange={e=>setTitle(e.target.value)} placeholder="e.g. Introduction to wave optics"/></label><label>Caption language<select value={language} onChange={e=>setLanguage(e.target.value)}>{[['en','English'],['hi','Hindi'],['kn','Kannada'],['ta','Tamil'],['te','Telugu'],['ml','Malayalam'],['mr','Marathi'],['bn','Bengali']].map(([code,label])=><option key={code} value={code}>{label}</option>)}</select></label></div>
        <label className="checkbox-label"><input type="checkbox" checked={manual} onChange={e=>setManual(e.target.checked)}/>Paste a transcript instead of fetching captions</label>
        {manual?<label>Lecture transcript<textarea required minLength={100} maxLength={250000} rows={7} value={transcript} onChange={e=>setTranscript(e.target.value)} placeholder="Paste a transcript you have access to. Pasted content is labelled as user-supplied and has no verified timestamps."/></label>:<p className="inline-note">Uses accessible captions in the selected language. If YouTube blocks access or captions are missing, paste a transcript instead.</p>}
        <button className="primary-button" type="submit">{saving?<><CircleNotch className="spinner" size={18}/>Registering...</>:'Import lecture'}</button>
      </fieldset></form>
    </details>
    {notice&&<p role="status" className="inline-note">{notice}</p>}
    {error&&<p role="alert" className="persona-error">{error}</p>}
    {available.map(educator=><details key={educator.id} className="educator-detail"><summary>{educator.name}<span>{educator.passage_count} passages · {educator.ready?'Ready':'Needs material'}</span></summary>
      {educator.descriptor&&<dl className="style-profile">{Object.entries(educator.descriptor).map(([key,value])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{value}</dd></div>)}</dl>}
      {educator.videos.map(video=><div key={video.id} className="lecture-status"><a href={video.url} target="_blank" rel="noreferrer">{video.title}</a><span>{video.status==='processing'?'Importing and analyzing style...':video.status==='ready'?`${video.passage_count} passages indexed`: 'Import failed'}{video.origin==='pasted'?' · User-supplied transcript':''}</span>{video.error&&<p className="persona-error">{video.error}</p>}{video.status==='failed'&&<button className="text-button" onClick={()=>{setExisting(educator.id);setUrl(video.url);setTitle(video.title);document.querySelector<HTMLDetailsElement>('.persona-register')!.open=true;}}>Retry this lecture</button>}</div>)}
    </details>)}
  </section>;
}
