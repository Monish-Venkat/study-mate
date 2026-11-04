import {NextRequest,NextResponse} from 'next/server';
const allowed:Record<string,string[]>={'mock-paper/score':['POST'],planner:['POST'],profile:['POST'],scores:['POST'],'memory/clear':['POST'],'voice/transcribe':['POST'],'voice/speak':['POST'],'teacher/analytics':['GET'],'teacher/syllabus':['POST'],'teacher/questions':['POST'],'teacher/upload':['POST']};
async function proxy(request:NextRequest,context:{params:Promise<{path:string[]}>}){
  const path=(await context.params).path.join('/');
  const methods=/^teacher\/uploads\/[a-f0-9]{32}$/.test(path)?['GET']:allowed[path];
  if(!methods?.includes(request.method))return NextResponse.json({detail:'Unknown operation.'},{status:404});
  const headers:Record<string,string>={};
  if(request.headers.get('content-type'))headers['Content-Type']=request.headers.get('content-type')!;
  if(path.startsWith('teacher/'))headers['X-Teacher-Key']=request.headers.get('x-teacher-key')||'';
  let body:ArrayBuffer|undefined;
  if(request.method==='POST'){
    body=await request.arrayBuffer();
    if(body.byteLength>21*1024*1024)return NextResponse.json({detail:'Upload is too large.'},{status:413});
  }
  try{
    const base=(process.env.BACKEND_URL||'http://127.0.0.1:8000').replace(/\/$/,'');
    const suffix=['planner','profile','scores'].includes(path)?'/':'';
    const response=await fetch(`${base}/${path}${suffix}`,{method:request.method,headers,body,cache:'no-store',signal:AbortSignal.timeout(180000)});
    if(response.headers.get('content-type')?.includes('audio/'))return new NextResponse(await response.arrayBuffer(),{status:response.status,headers:{'Content-Type':'audio/mpeg','Cache-Control':'no-store'}});
    const data=await response.json();
    if(Array.isArray(data.detail))data.detail=data.detail.map((d:{loc?:string[];msg?:string})=>`${d.loc?.slice(1).join('.')}: ${d.msg}`).join('; ');
    return NextResponse.json(data,{status:response.status});
  }catch{return NextResponse.json({detail:'The service is unavailable or took too long. Check the backend and required models.'},{status:503});}
}
export const GET=proxy;
export const POST=proxy;
