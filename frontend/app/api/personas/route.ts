import {NextRequest,NextResponse} from 'next/server';
async function proxy(request:NextRequest) {
  let body;
  if(request.method==='POST') {
    const raw=await request.text();
    if(raw.length>260000) return NextResponse.json({detail:'Transcript is too long. Use a shorter lecture.'},{status:413});
    try {body=JSON.stringify(JSON.parse(raw));} catch {return NextResponse.json({detail:'Invalid registration request.'},{status:400});}
  }
  try {
    const base=(process.env.BACKEND_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
    // Registration fetches captions and embeds every transcript chunk, so a
    // full-length lecture needs far longer than a plain listing.
    const timeout=request.method==='POST'?Number(process.env.PERSONA_TIMEOUT_MS)||600000:15000;
    const response=await fetch(`${base}/personas/`,{method:request.method,headers:{'Content-Type':'application/json'},body,cache:'no-store',signal:AbortSignal.timeout(timeout)});
    const data=await response.json();
    if(!response.ok&&Array.isArray(data.detail)) data.detail='Check the educator name, video URL, subject and transcript length (100 to 250,000 characters).';
    return NextResponse.json(data,{status:response.status});
  } catch {return NextResponse.json({detail:'The persona service is unavailable. Start the backend and refresh.'},{status:503});}
}
export const GET=proxy;
export const POST=proxy;
