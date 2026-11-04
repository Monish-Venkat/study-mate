import re
import asyncio
from app.services.faiss_store import store
from app.services.embeddings import embed_text
from app.services.llm_client import generate_text
from app.core.config import settings
from app.core.prompts import ask_prompt, socratic_prompt, summary_prompt, mock_prompt, pyq_prompt

# Front matter is lexically dense in the subject name, so it out-ranks real
# chapters for broad queries. Catching it by content costs nothing at query time.
# "Reprint 20xx-xx" sits in the footer of every NCERT page, so it is a page
# marker rather than a front-matter signal and must not appear here.
# Strong markers name the apparatus of a book; a chapter explaining physics has
# no reason to use them even once.
_STRONG = re.compile(
    r'\b(preface|foreword|table of contents|rationalis(?:ed|ation) of content|'
    r'isbn|published by|publication division|national council of educational|'
    r'chief advisor|advisory committee|textbook development committee)\b', re.I)
# Weak markers also occur in ordinary prose, so they need corroboration.
_WEAK = re.compile(r'\b(contents|acknowledgement|committee|coordinator|editor)\b', re.I)
# A title page is mostly its own title.
_TITLE_PAGE = re.compile(r'^\W*\w*\s*(physics|chemistry|mathematics|biology)\s+part\s*[–\-—]\s*[iv]+', re.I)


def is_boilerplate(text):
    """Front matter: publisher apparatus rather than examinable content."""
    words = text.split()
    if len(words) < 12:
        return True
    if _TITLE_PAGE.match(text.strip()):
        return True
    if _STRONG.search(text):
        return True
    return len(_WEAK.findall(text)) >= 2


def build_context(hits):
    return '\n\n'.join(f"[{i}] {h.get('source', 'unknown')}, page {h.get('page', '?')}: {h['text']}" for i, h in enumerate(hits, 1))

async def retrieve(question, subject, level, board, doc_types, top_k=None):
    if not store.index.ntotal:
        return []
    normalized_level = {'PUC1': '1st', 'PUC2': '2nd'}.get(level.upper(), level.lower())
    filters = {'subject': [subject.lower()], 'level': [normalized_level],
               'board': [board.lower()], 'doc_type': doc_types}
    limit = top_k or settings.TOP_K
    vec = await asyncio.to_thread(embed_text, question)
    if not settings.ENABLE_HYBRID:
        return await asyncio.to_thread(store.search, vec, limit, filters)
    return await asyncio.to_thread(_hybrid, question, vec, limit, filters)


def _hybrid(question, vec, limit, filters):
    """Dense and lexical arms, fused by rank rather than by score."""
    from app.services.lexical import fuse, lexical_hits
    candidates = max(settings.HYBRID_CANDIDATES, limit)
    dense = store.search(vec, candidates, filters)
    lexical = lexical_hits(question, vec, store, filters, candidates)
    if not lexical:
        return dense[:limit]
    return fuse(dense, lexical, limit)

async def respond(query, subject, level, board, model, make_prompt, doc_types=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None):
    from app.services.crag import corrective_retrieve
    hits, telemetry = await corrective_retrieve(
        query, subject, level, board, doc_types or ['textbook', 'syllabus'], retrieve)
    if retrieval_result is not None:
        retrieval_result.update(telemetry)
    if not hits:
        if persona_result is not None and persona_id:
            persona_result.update(applied=False, reason='No course evidence was found, so persona styling was not used.')
        return 'I could not find supporting passages for this request in the selected course material. Check your subject and year, or ask for the relevant material to be indexed.'
    prefix = ''
    if persona_id:
        from app.services.persona import style_context
        prefix, metadata = await style_context(persona_id, subject, query)
        if persona_result is not None:
            persona_result.update(metadata)
    answer = await generate_text(model, prefix + dialogue_context + make_prompt(build_context(hits)))
    answer = await _audit(answer, hits, grounding_result)
    sources = '\n'.join(f"[{i}] {h['source']} | page {h.get('page', '?')}" for i, h in enumerate(hits, 1))
    return f'{answer}\n\nRetrieved sources\n{sources}'

async def _audit(answer, hits, grounding_result):
    """Read the answer back against its evidence and append an honest caveat.

    The caveat is appended to the answer text rather than left only in the
    structured report, so every surface -- web, Telegram, voice -- carries the
    warning without each having to know that the audit exists.
    """
    if not settings.ENABLE_GROUNDING:
        return answer
    from app.services.grounding import audit, caveat, verify
    report = audit(answer, hits)
    flagged = report['counts']['unsupported'] + report['counts']['miscited']
    if settings.ENABLE_GROUNDING_VERIFY and flagged:
        report = await verify(report, hits)
    if grounding_result is not None:
        grounding_result.update(report)
    note = caveat(report)
    return answer + '\n\n' + note if note else answer

async def run_ask(question, subject, level, board, chapter=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None):
    return await respond(f'{chapter or ""} {question}', subject, level, board, settings.LLM_MAIN_MODEL,
                         lambda ctx: ask_prompt(ctx, question, board, level, subject), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result, grounding_result=grounding_result)

async def run_socratic(question, subject, level, board, chapter=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None):
    return await respond(f'{chapter or ""} {question}', subject, level, board, settings.LLM_SOCRATIC_MODEL,
                         lambda ctx: socratic_prompt(ctx, question, board, level, subject), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result, grounding_result=grounding_result)

async def run_summary(chapter, subject, level, board, summary_type, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None):
    return await respond(chapter, subject, level, board, settings.LLM_SMALL_MODEL,
                         lambda ctx: summary_prompt(ctx, chapter, board, level, subject, summary_type), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result)

async def run_pyq(subject, level, board):
    return await respond(subject, subject, level, board, settings.LLM_SMALL_MODEL,
                         lambda ctx: pyq_prompt(ctx, subject, board, level), ['question_paper'])

async def run_mock(subject, level, board, total_marks):
    return await respond(subject, subject, level, board, settings.LLM_MOCK_MODEL,
                         lambda ctx: mock_prompt(ctx, subject, board, level, total_marks))
