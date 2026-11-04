from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.routers import health, ask, socratic, summary, pyq, mock_paper, persona, learning, voice, teacher, telegram, diagram
from contextlib import asynccontextmanager, suppress
import asyncio
import time
from collections import defaultdict, deque
from app.services.persona_store import persona_store
from app.services.llm_client import GenerationUnavailable

@asynccontextmanager
async def lifespan(app):
    persona_store().recover()
    task = asyncio.create_task(telegram.worker()) if settings.TELEGRAM_BOT_TOKEN else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

app = FastAPI(title=settings.APP_NAME, version='4.1.0', lifespan=lifespan)
for router in (health, ask, socratic, summary, pyq, mock_paper, persona, learning, voice, teacher, telegram, diagram):
    app.include_router(router.router)

@app.exception_handler(GenerationUnavailable)
async def generation_unavailable(request: Request, exc: GenerationUnavailable):
    return JSONResponse(status_code=503, content={'detail': str(exc)})

@app.get('/')
def root():
    return {'app': settings.APP_NAME, 'docs': '/docs'}

_hits = defaultdict(deque)
@app.middleware('http')
async def protections(request: Request, call_next):
    client = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    bucket = _hits[client]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE:
        return JSONResponse(status_code=429, content={'detail':'Too many requests. Please retry in a minute.'}, headers={'Retry-After':'60'})
    bucket.append(now)
    if len(_hits) > 10000:
        for ip in list(_hits):
            if not _hits[ip] or _hits[ip][-1] < now-60:
                del _hits[ip]
    try:
        length = int(request.headers.get('content-length','0'))
    except ValueError:
        return JSONResponse(status_code=400,content={'detail':'Invalid content length.'})
    maximum = 21*1024*1024 if request.url.path in ('/teacher/upload','/voice/transcribe') else 2*1024*1024
    if length > maximum:
        return JSONResponse(status_code=413,content={'detail':'Request too large.'})
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
