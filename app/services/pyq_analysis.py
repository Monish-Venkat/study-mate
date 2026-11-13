"""Reproducible topic statistics across the available five-year question archive."""
import json
import math
import re
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
from pypdf import PdfReader
from app.core.config import settings
from app.services.ingest import infer_subject_level

STOP=set('the and for with that this from which what when where why how are was were have has had into explain describe define state find calculate write give following question questions answer answers marks mark part section any all each its their two three one using show prove obtain draw about based not you your can will a an of to in on is it as be by or at'.split())

def words(text):
    return [w for w in re.findall(r'[a-zA-Z]{3,}',text.lower()) if w not in STOP]


def phrases(text):
    """Unigrams plus adjacent bigrams.

    Single tokens are not topics: "electric" is the top keyword for half a
    physics paper and tells a student nothing. A bigram separates "electric
    field" from "electric potential", which are different questions with
    different answers.
    """
    tokens=words(text)
    return tokens+[f'{a} {b}' for a,b in zip(tokens,tokens[1:])]


def _vectors(texts):
    """Embed question texts, or return None when the model is unavailable."""
    try:
        from app.services.embeddings import embed_texts
        import numpy as np
        arr=np.asarray(embed_texts(texts),dtype='float32')
        norms=np.linalg.norm(arr,axis=1,keepdims=True)
        return arr/np.clip(norms,1e-9,None)
    except Exception:
        return None


def cluster_questions(records,floor=0.62):
    """Group questions that ask the same thing, however they are worded.

    Keyword counting cannot see that "derive an expression for the electric
    field due to a dipole" and "obtain E for a short dipole on its axial
    line" are one recurring question. Cosine similarity over the same encoder
    the rest of the system uses can, so clustering happens in embedding space
    and falls back to exact-ish text grouping when no model is reachable.
    """
    if not records:
        return []
    matrix=_vectors([r['text'][:600] for r in records])
    if matrix is None:
        return [[r] for r in records]
    # Greedy: each question joins the first centroid it is close enough to.
    # Agglomerative would be better but this stays linear and is stable.
    centroids=[]
    clusters=[]
    import numpy as np
    for index,row in enumerate(matrix):
        best,score=-1,floor
        for position,centroid in enumerate(centroids):
            similarity=float(np.dot(centroid,row))
            if similarity>=score:
                best,score=position,similarity
        if best<0:
            centroids.append(row.copy())
            clusters.append([index])
        else:
            members=clusters[best]
            members.append(index)
            updated=centroids[best]*len(members[:-1])+row
            centroids[best]=updated/max(1e-9,float(np.linalg.norm(updated)))
    return [[records[i] for i in members] for members in clusters]


def label_cluster(cluster,document_frequency,total):
    """Name a cluster by the phrases that distinguish it from the rest."""
    counts=Counter()
    for record in cluster:
        counts.update(set(phrases(record['text'])))
    scored=[]
    for phrase,n in counts.items():
        if n<max(1,len(cluster)//2):continue
        weight=(n/len(cluster))*math.log((1+total)/(1+document_frequency.get(phrase,0)))
        # Prefer the two-word form: it is the one that reads as a topic.
        scored.append((weight*(1.6 if ' ' in phrase else 1.0),phrase))
    scored.sort(reverse=True)
    chosen=[]
    for _,phrase in scored:
        if any(phrase in picked or picked in phrase for picked in chosen):continue
        chosen.append(phrase)
        if len(chosen)==3:break
    return ', '.join(chosen) or 'unlabelled'


def study_reference(cluster,subject,level,board):
    """Where in the textbook this recurring question is answered."""
    try:
        from app.services.embeddings import embed_text
        from app.services.faiss_store import store
        sample=max(cluster,key=lambda r:len(r['text']))['text'][:400]
        normalised={'PUC1':'1st','PUC2':'2nd'}.get(level.upper(),level.lower())
        hits=store.search(embed_text(sample),2,
                          {'subject':[subject.lower()],'level':[normalised],
                           'doc_type':['textbook','syllabus']})
        return [{'source':h['source'],'page':h.get('page')} for h in hits]
    except Exception:
        return []

def text_quality(text):
    """Fraction of Latin letters, and of private-use glyphs, in extracted text.

    The Kannada-medium board papers embed a custom-encoded font with no
    ToUnicode map, so their glyphs extract as U+E000..U+F8FF rather than as
    characters. Nothing downstream can read that: the words are simply not
    recoverable. Without this check those pages produced question records
    whose text was punctuation and option letters, and keyword analysis then
    reported them as recurring topics.
    """
    if not text:
        return 0.0,0.0
    total=len(text)
    latin=sum(c.isascii() and c.isalpha() for c in text)
    private=sum(0xE000<=ord(c)<=0xF8FF for c in text)
    return latin/total,private/total


MIN_LATIN=0.25
MAX_PRIVATE=0.15

# A numbered line is not necessarily a question. Papers open with rubric
# ("All parts are compulsory", "problems without relevant formula carry no
# marks") which is numbered exactly like the questions and was being counted
# as one, so instructions appeared in the report as recurring topics.
ASK=re.compile(r'\b(explain|describe|define|state|derive|obtain|calculate|find|determine|'
               r'write|mention|name|list|show|prove|draw|sketch|compare|distinguish|'
               r'differentiate|what|why|how|which|when|where|give|identify|classify|'
               r'deduce|establish|arrive|discuss)\b',re.I)
RUBRIC=re.compile(r'\b(compulsory|carry no marks|wherever necessary|answer will be|'
                  r'figures? in the right|right hand margin|for part|instructions?|'
                  r'maximum marks|time allowed|candidates?|answer booklet)\b',re.I)


def looks_like_question(body):
    """Keep numbered items that actually ask something."""
    if RUBRIC.search(body):
        return False
    return bool('?' in body or ASK.search(body))


# Adobe Symbol font mapped onto the Private Use Area: a Symbol-encoded "m"
# arrives as U+F06D rather than as "mu". The page is otherwise perfectly
# readable English, so the ratio gate above passes it — correctly — but the
# individual glyph still reaches a student as an empty box. "3 uF" matters in
# a capacitance question, so the common Symbol codepoints are mapped back.
_SYMBOL_PUA = {
    0xF061: 'α', 0xF062: 'β', 0xF063: 'χ', 0xF064: 'δ', 0xF065: 'ε', 0xF066: 'φ',
    0xF067: 'γ', 0xF068: 'η', 0xF069: 'ι', 0xF06A: 'φ', 0xF06B: 'κ', 0xF06C: 'λ',
    0xF06D: 'μ', 0xF06E: 'ν', 0xF06F: 'ο', 0xF070: 'π', 0xF071: 'θ', 0xF072: 'ρ',
    0xF073: 'σ', 0xF074: 'τ', 0xF075: 'υ', 0xF077: 'ω', 0xF078: 'ξ', 0xF079: 'ψ',
    0xF07A: 'ζ',
    0xF041: 'Α', 0xF042: 'Β', 0xF044: 'Δ', 0xF046: 'Φ', 0xF047: 'Γ', 0xF04C: 'Λ',
    0xF050: 'Π', 0xF051: 'Θ', 0xF053: 'Σ', 0xF057: 'Ω', 0xF058: 'Ξ', 0xF059: 'Ψ',
    0xF0A3: '≤', 0xF0A5: '∞', 0xF0AC: '←', 0xF0AD: '↑', 0xF0AE: '→', 0xF0AF: '↓',
    0xF0B0: '°', 0xF0B1: '±', 0xF0B3: '≥', 0xF0B4: '×', 0xF0B6: '∂', 0xF0B7: '·',
    0xF0B8: '÷', 0xF0B9: '≠', 0xF0BB: '≈', 0xF0D6: '√', 0xF0F2: '∫',
    # Symbol keeps ASCII punctuation at its ASCII position, so these map to
    # themselves. A bracketed unit — "[AT]" in a matching-columns question —
    # arrived as two empty boxes without them.
    0xF028: '(', 0xF029: ')', 0xF02B: '+', 0xF02D: '−', 0xF02F: '/',
    0xF03D: '=', 0xF05B: '[', 0xF05D: ']', 0xF07B: '{', 0xF07D: '}',
}


def repair_symbol_font(text):
    """Map Symbol-font private-use codepoints back to real characters."""
    return text.translate(_SYMBOL_PUA) if text else text


def classify_source(name):
    """What kind of document this is, which decides what it may be evidence of.

    A board paper is evidence of what gets asked: the same topic appearing in
    several years is a trend. A question bank is not — it holds many questions
    per topic by construction, so counting its entries as recurrence would
    manufacture a trend out of an editorial decision. Both are useful, so both
    are read, but they are counted separately and never summed.
    """
    lower=name.lower()
    if any(tag in lower for tag in ('_qb','question_bank')):
        return 'bank'
    if '_sov' in lower:
        return 'solved'
    return 'paper'


KIND_LABEL={'paper':'board paper','bank':'question bank','solved':'solved paper'}


def question_records(subject,level,board):
    curated=Path(settings.DATA_DIR)/'pyq_questions.json'
    if curated.exists():
        records=json.loads(curated.read_text(encoding='utf-8'))
        selected=[r for r in records if (r['subject'],r['level'],r['board'])==(subject,level,board)]
        if selected:return selected,'teacher-curated',[]
    result=[]
    skipped=[]
    normalized={'PUC1':'1st','PUC2':'2nd'}[level]
    for path in Path(settings.QUESTION_PAPERS_DIR).rglob('*.pdf'):
        if infer_subject_level(path)!=(subject,normalized,board.lower()):continue
        kind=classify_source(path.name)
        years=re.findall(r'20\d{2}',path.name)
        # Only a board paper needs a year: it is the year that makes it
        # evidence of a trend. A bank contributes practice volume regardless.
        if kind=='paper' and not years:
            skipped.append({'file':path.name,'reason':'no year in the filename'})
            continue
        try:
            unreadable=0
            pages_seen=0
            for page_number,page in enumerate(PdfReader(path).pages,1):
                text=page.extract_text() or ''
                pages_seen+=1
                latin,private=text_quality(text)
                if len(text)>80 and (latin<MIN_LATIN or private>MAX_PRIVATE):
                    unreadable+=1
                    continue
                matches=list(re.finditer(r'(?m)^\s*(\d{1,3})[.)]\s+',text))
                for i,match in enumerate(matches):
                    body=text[match.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
                    body=repair_symbol_font(body)
                    if len(body)<15 or not looks_like_question(body):continue
                    mark=re.search(r'(?:\[|\()\s*(\d{1,2})\s*(?:marks?)?\s*[\])]|(\d{1,2})\s*marks?\b',body,re.I)
                    result.append({'subject':subject,'level':level,'board':board,
                                   'year':int(years[0]) if years else None,'text':body[:4000],
                                   'marks':int(next(g for g in mark.groups() if g)) if mark else None,
                                   'source':path.name,'page':page_number,'topic':None,
                                   'kind':kind,'verified':False})
            if pages_seen and unreadable/pages_seen>0.5:
                skipped.append({'file':path.name,
                                'reason':f'text not extractable on {unreadable} of {pages_seen} pages '
                                         '(the PDF embeds a private-use font, typical of the '
                                         'Kannada-medium papers)'})
        except Exception as exc:
            skipped.append({'file':path.name,'reason':f'could not be read ({type(exc).__name__})'})
            continue
    return result,'automatic PDF extraction (unreviewed)',skipped

def trend_report(records,current_year=None,subject=None,level=None,board=None):
    end=current_year or date.today().year
    window=list(range(end-4,end+1))
    # Only board papers are windowed: the window exists to bound a trend, and
    # a bank is not evidence of one.
    records=[r for r in records if r.get('kind','paper')!='paper' or r.get('year') in window]
    unique={}
    for r in records:unique[(r['source'],r.get('year'),' '.join(r['text'].split()))]=r
    records=list(unique.values())
    papers_only=[r for r in records if r.get('kind','paper')=='paper']

    explicit=sorted({r.get('topic') for r in records if r.get('topic')})
    document_frequency=Counter()
    for record in records:
        document_frequency.update(set(phrases(record['text'])))

    topics=[]
    if explicit:
        # A teacher-curated set already names the topics; use them as given.
        groups=[(term,[r for r in records if r.get('topic')==term]) for term in explicit]
        grouping='teacher-labelled topics'
    else:
        clusters=cluster_questions(records)
        groups=[(label_cluster(c,document_frequency,len(records)),c) for c in clusters]
        grouping='questions grouped by meaning, labelled by distinguishing phrase'

    for name,group in groups:
        if not group:continue
        marks=[r['marks'] for r in group if r.get('marks')]
        example=min(group,key=lambda r:len(r['text']))['text']
        in_papers=[r for r in group if r.get('kind','paper')=='paper']
        in_banks=[r for r in group if r.get('kind') in ('bank','solved')]
        topics.append({
            'topic':name,
            'question_count':len(group),
            'paper_count':len(in_papers),
            'bank_count':len(in_banks),
            # Years come from board papers alone: a bank entry has no exam year.
            'years':sorted({r['year'] for r in in_papers if r.get('year')}),
            'known_marks':sum(marks),
            'typical_marks':max(set(marks),key=marks.count) if marks else None,
            # One real question stands in for the group: a student recognises
            # the thing being asked faster from an example than from a label.
            'example':' '.join(example.split())[:220],
            'study':study_reference(group,subject,level,board) if subject else [],
        })
    # Recurrence across exam years first, then how often it is asked at all.
    topics.sort(key=lambda t:(len(t['years']),t['paper_count'],t['question_count']),reverse=True)

    distribution=Counter('unknown' if r.get('marks') is None else 'short' if r['marks']<=2 else 'mid' if r['marks']<=5 else 'long' for r in records)
    available=sorted({r['year'] for r in papers_only if r.get('year')})
    composition=Counter(r.get('kind','paper') for r in records)
    return {'window':window,'available_years':available,'missing_years':[y for y in window if y not in available],
            'question_count':len(records),'paper_question_count':len(papers_only),
            'bank_question_count':len(records)-len(papers_only),
            'composition':{KIND_LABEL.get(k,k):n for k,n in composition.items()},
            'topics':topics,'grouping':grouping,
            'mark_distribution':dict(distribution),
            'sources':sorted({r['source'] for r in records}), 'verified':bool(records) and all(r.get('verified',False) for r in records)}

def analyze(subject,level,board):
    records,origin,skipped=question_records(subject,level,board)
    report=trend_report(records,subject=subject,level=level,board=board)
    report['skipped_files']=skipped
    # Blocks are joined with a blank line between them, but a markdown table
    # only parses when its rows sit on consecutive lines.
    composition=', '.join(f'{n} from {label}s' for label,n in sorted(report.get('composition',{}).items()))
    lines=['## Previous-year question analysis','',
           f"Dataset: {origin}. Questions: {report['question_count']}"
           +(f' ({composition})' if composition else '')+'.','',
           f"Board-paper years available: {', '.join(map(str,report['available_years'])) or 'none'}.",'',
           f"Missing years in the five-year window: {', '.join(map(str,report['missing_years'])) or 'none'}.",'',
           'Recurrence is counted from board papers only. Question-bank entries show how much '
           'practice exists on a topic, which is an editorial choice by the compiler rather than '
           'evidence of what the board asks.']
    lines+=['',f"Grouping: {report['grouping']}."]
    if not report['verified']:
        lines+=['','Extraction and grouping are automatic. Review them before drawing exam predictions.']
    recurring=[t for t in report['topics'] if t['paper_count']>1 or len(t['years'])>1]
    if recurring:
        lines+=['','| Recurring topic | In board papers | Years | Practice questions | Typical marks |',
                '|---|---:|---|---:|---:|']
        lines+=[f"| {t['topic']} | {t['paper_count']} | {', '.join(map(str,t['years'])) or '-'} "
                f"| {t['bank_count']} | {t['typical_marks'] if t['typical_marks'] else '-'} |"
                for t in recurring[:12]]
    elif report['topics']:
        # Calling a question asked once in one paper a "trend" would be the
        # exact overclaim this report exists to avoid.
        covered=[t for t in report['topics'] if t['bank_count']>1]
        lines+=['',f"No question recurred across board papers: "
                   f"{report['paper_question_count']} board-paper questions were found across "
                   f"{len(report['available_years'])} year"
                   f"{'' if len(report['available_years'])==1 else 's'}, each asked once."]
        if covered:
            covered.sort(key=lambda t:t['bank_count'],reverse=True)
            lines+=['',f"The question banks do show where practice is concentrated, which is a "
                       f"weaker signal but still worth working through:",'',
                    '| Topic | Practice questions |','|---|---:|']
            lines+=[f"| {t['topic']} | {t['bank_count']} |" for t in covered[:12]]
    highlights=recurring[:6] if recurring else report['topics'][:6]
    if highlights:
        # The table says what recurs; these say what the question looked like
        # and where it is answered, which is what a student acts on.
        lines+=['','### '+('What these look like' if recurring else 'Questions found, and where they are answered'),'']
        for topic in highlights:
            where=', '.join(f"{s['source']} p. {s['page']}" for s in topic['study'] if s.get('page'))
            # Papers and banks are never added together: one says what the
            # board asked, the other says how much practice a compiler wrote.
            counts=[]
            if topic['paper_count']:
                years=', '.join(map(str,topic['years'])) or 'year not stated'
                counts.append(f"{topic['paper_count']} board-paper question"
                              f"{'' if topic['paper_count']==1 else 's'} ({years})")
            if topic['bank_count']:
                counts.append(f"{topic['bank_count']} practice question"
                              f"{'' if topic['bank_count']==1 else 's'} in the banks")
            lines+=[f"**{topic['topic']}** — {', '.join(counts)}.",'',f"> {topic['example']}",'']
            if where:
                lines+=[f'Study this in: {where}','']
    else:
        lines+=['','No usable questions were found for this subject and year. '
                   'Add teacher-curated question records, or supply the English-medium paper.']
    if report.get('skipped_files'):
        # Saying which papers were not read, and why, is the difference between
        # "no trends found" and a student believing there are none.
        lines+=['','### Papers not used','']
        lines+=[f"- **{s['file']}** — {s['reason']}" for s in report['skipped_files']]
    lines+=['','Mark distribution: '+json.dumps(report['mark_distribution'])]
    return {'analysis':'\n'.join(lines),'report':report}
