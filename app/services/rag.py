import re
import asyncio
from app.services.faiss_store import store
from app.services.embeddings import embed_text
from app.services.llm_client import TUTOR_SYSTEM_PROMPT, generate_text
from app.services.answer_text import drop_repeats
from app.core.config import settings
from app.core.prompts import LANGUAGES, LEVELS, language_directive, language_system, ask_prompt, socratic_prompt, summary_prompt, mock_prompt, pyq_prompt

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

async def respond(query, subject, level, board, model, make_prompt, doc_types=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None, language='en'):
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
    # A non-English answer is only attempted on a model that can actually
    # write the language. Without one, the request is served in English and
    # said so below, because what the local models produced instead was
    # fluent nonsense in the correct script. See LLM_MULTILINGUAL_MODEL.
    served = language if (language == 'en' or settings.LLM_MULTILINGUAL_MODEL) else 'en'
    if served != 'en':
        model = settings.LLM_MULTILINGUAL_MODEL
    # The language directive goes LAST, after the question and the English
    # passages, because that is the only position a small model reliably
    # obeys it from; the system line repeats it. Stated once at the front,
    # as it was, every reply came back in English.
    prompt = prefix + dialogue_context + make_prompt(build_context(hits)) + language_directive(served)
    system = TUTOR_SYSTEM_PROMPT + language_system(served)
    answer = await generate_text(model, prompt, system=system)
    # Before the audit, so a restated point is not counted, verified and
    # warned about several times over as though it were several claims.
    answer = drop_repeats(answer)
    answer, report = await _audit(answer, hits, grounding_result)
    if _should_abstain(report, telemetry):
        if grounding_result is not None:
            grounding_result['withheld'] = True
        answer = _abstention(subject, level, report)
    # Tell the student plainly rather than quietly answering in the wrong
    # language. Nothing downstream can catch the alternative: the grounding
    # audit matches English passages and scored the nonsense version 1.0.
    if served != language:
        answer += ('\n\nThis answer is in English. ' + LANGUAGES.get(language, language)
                   + ' is not available on the model this install runs; an answer written '
                     'in invented terminology would cost you marks, so it was not attempted.')
    sources = '\n'.join(f"[{i}] {h['source']} | page {h.get('page', '?')}" for i, h in enumerate(hits, 1))
    return f'{answer}\n\nRetrieved sources\n{sources}'


# Corrective-retrieval outcomes that mean the grader found nothing supporting
# the question as the student asked it. "incorrect_recovered" is included
# because the recovery came from a rewritten query, not from the question --
# the Euglena answer took that path, scored 0.5 traceable, and still stated
# that Euglena has two flagella when it has one. "ambiguous" is deliberately
# left out: it means partial evidence was there from the start, and holding it
# to the higher bar would withhold answers that are merely incomplete.
WEAK_RETRIEVAL = frozenset({'incorrect', 'incorrect_recovered'})


def _should_abstain(report, telemetry):
    """Is the answer so far from its evidence that it should not be shown?

    Judged on the finished answer rather than on the passages, because the
    failure being caught happens after retrieval: the model is handed thin
    evidence and completes the answer from parametric memory instead of
    saying it cannot. The corrective layer grades passages and never sees
    that, which is why a question graded 'incorrect' still produced a fluent,
    wrong answer about Euglena.
    """
    if not (settings.ENABLE_GROUNDING and settings.ABSTAIN_ON_UNGROUNDED):
        return False
    # No claims parsed means there is nothing to judge. Show the answer rather
    # than withhold one because the claim splitter found nothing to split.
    counts = (report or {}).get('counts') or {}
    if not sum(counts.values()):
        return False
    floor = (settings.ABSTAIN_GROUNDED_FRACTION_WEAK
             if (telemetry or {}).get('action') in WEAK_RETRIEVAL
             else settings.ABSTAIN_GROUNDED_FRACTION)
    return report.get('grounded_fraction', 1.0) < floor


def _abstention(subject, level, report):
    """What to say instead of a confidently wrong answer.

    Not a dead end: the retrieved passages are still listed below this, so a
    student gets the material that does exist and can judge it themselves.
    """
    traced = int(round(report.get('grounded_fraction', 0.0) * 100))
    return (
        'StudyMate has not answered this.\n\n'
        f'A draft answer was written and then checked against the indexed {subject} material '
        f'for {LEVELS.get(level, level)}: only {traced}% of it could be traced back to those '
        f'passages. The rest '
        'came from the model rather than from your course material, so it is not safe to '
        'revise from and has been withheld.\n\n'
        'What you can do:\n'
        '1. Check the passages listed below, which are the closest material the index holds.\n'
        '2. Ask about a narrower part of the topic, in the wording the textbook uses.\n'
        '3. If the chapter should be covered, ask for it to be indexed: a topic that is not in '
        'the index cannot be answered from it.'
    )

async def _audit(answer, hits, grounding_result):
    """Read the answer back against its evidence and append an honest caveat.

    The caveat is appended to the answer text rather than left only in the
    structured report, so every surface -- web, Telegram, voice -- carries the
    warning without each having to know that the audit exists.
    """
    if not settings.ENABLE_GROUNDING:
        return answer, {}
    from app.services.grounding import audit, caveat, verify
    report = audit(answer, hits)
    flagged = report['counts']['unsupported'] + report['counts']['miscited']
    if settings.ENABLE_GROUNDING_VERIFY and flagged:
        report = await verify(report, hits)
    if grounding_result is not None:
        grounding_result.update(report)
    note = caveat(report)
    return (answer + '\n\n' + note if note else answer), report

async def run_ask(question, subject, level, board, chapter=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None, language='en'):
    return await respond(f'{chapter or ""} {question}', subject, level, board, settings.LLM_MAIN_MODEL,
                         lambda ctx: ask_prompt(ctx, question, board, level, subject), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result, grounding_result=grounding_result, language=language)

async def run_socratic(question, subject, level, board, chapter=None, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, grounding_result=None, language='en'):
    return await respond(f'{chapter or ""} {question}', subject, level, board, settings.LLM_SOCRATIC_MODEL,
                         lambda ctx: socratic_prompt(ctx, question, board, level, subject), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result, grounding_result=grounding_result, language=language)

async def run_summary(chapter, subject, level, board, summary_type, persona_id=None, persona_result=None, dialogue_context="", retrieval_result=None, language='en'):
    return await respond(chapter, subject, level, board, settings.LLM_SMALL_MODEL,
                         lambda ctx: summary_prompt(ctx, chapter, board, level, subject, summary_type), persona_id=persona_id, persona_result=persona_result, dialogue_context=dialogue_context, retrieval_result=retrieval_result, language=language)

async def run_pyq(subject, level, board):
    return await respond(subject, subject, level, board, settings.LLM_SMALL_MODEL,
                         lambda ctx: pyq_prompt(ctx, subject, board, level), ['question_paper'])

async def run_mock(subject, level, board, total_marks):
    return await respond(subject, subject, level, board, settings.LLM_MOCK_MODEL,
                         lambda ctx: mock_prompt(ctx, subject, board, level, total_marks))
