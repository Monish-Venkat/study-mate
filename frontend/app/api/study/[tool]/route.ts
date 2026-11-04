import { NextRequest, NextResponse } from 'next/server';
const routes: Record<string, string> = {ask:'ask/', socratic:'socratic/', summary:'summary/', pyq:'pyq/', 'mock-paper':'mock-paper/', diagram:'diagram/', health:'health'};
async function proxy(request: NextRequest, context: {params: Promise<{tool: string}>}) {
  const {tool} = await context.params;
  if (!routes[tool] || (request.method === 'GET') !== (tool === 'health')) return NextResponse.json({detail:'Unknown study tool.'}, {status:404});
  let body;
  if (request.method === 'POST') {
    try { body = JSON.stringify(await request.json()); }
    catch { return NextResponse.json({detail:'Please send a valid request.'}, {status:400}); }
    if (body.length > 16000) return NextResponse.json({detail:'Your request is too long.'}, {status:413});
  }
  try {
    const base = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
    // A local 7B model on a CPU-only host answers in minutes, not seconds.
    const studyTimeout = Number(process.env.STUDY_TIMEOUT_MS) || 900000;
    const response = await fetch(`${base}/${routes[tool]}`, {method:request.method, headers:{'Content-Type':'application/json'}, body, cache:'no-store', signal:AbortSignal.timeout(tool === 'health' ? 5000 : studyTimeout)});
    const data = await response.json();
    return NextResponse.json(data, {status:response.status});
  } catch {
    return NextResponse.json({detail:'The study service could not be reached. Start the Python backend and try again.'}, {status:503});
  }
}
export const GET = proxy;
export const POST = proxy;
