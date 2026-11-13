import { NextRequest, NextResponse } from 'next/server';
import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';

const routes: Record<string, string> = {ask:'ask/', socratic:'socratic/', summary:'summary/', pyq:'pyq/', 'mock-paper':'mock-paper/', diagram:'diagram/', health:'health'};

// Why this is not fetch: Node's fetch is undici, whose headersTimeout defaults
// to 300s and is NOT governed by the AbortSignal below. A 35-mark practice
// paper on a local 7B CPU model takes five to eight minutes and sends no
// response headers until it is finished, so every paper died at 5.1 minutes
// with "the study service could not be reached" while the backend was still
// working and went on to finish the paper. node:http imposes no header
// deadline of its own, so the one timeout here is the only one that applies.
// This route runs on the nodejs runtime, which is the default.
function call(url: string, method: string, body: string | undefined,
              timeoutMs: number): Promise<{status: number; text: string}> {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const send = target.protocol === 'https:' ? httpsRequest : httpRequest;
    const headers: Record<string, string | number> = {'Content-Type': 'application/json'};
    if (body !== undefined) headers['Content-Length'] = Buffer.byteLength(body);
    const req = send({
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || (target.protocol === 'https:' ? 443 : 80),
      path: target.pathname + target.search,
      method,
      headers,
    }, response => {
      let text = '';
      response.setEncoding('utf8');
      response.on('data', chunk => { text += chunk; });
      response.on('end', () => resolve({status: response.statusCode ?? 502, text}));
      response.on('error', reject);
    });
    req.setTimeout(timeoutMs, () => req.destroy(new Error('Timed out waiting for the study service')));
    req.on('error', reject);
    if (body !== undefined) req.write(body);
    req.end();
  });
}

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
    const {status, text} = await call(`${base}/${routes[tool]}`, request.method, body, tool === 'health' ? 5000 : studyTimeout);
    let data;
    try { data = JSON.parse(text); }
    catch { return NextResponse.json({detail:'The study service returned a malformed response.'}, {status:502}); }
    return NextResponse.json(data, {status});
  } catch {
    return NextResponse.json({detail:'The study service could not be reached. Start the Python backend and try again.'}, {status:503});
  }
}
export const GET = proxy;
export const POST = proxy;
