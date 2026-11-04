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

def question_records(subject,level,board):
    curated=Path(settings.DATA_DIR)/'pyq_questions.json'
    if curated.exists():
        records=json.loads(curated.read_text(encoding='utf-8'))
        selected=[r for r in records if (r['subject'],r['level'],r['board'])==(subject,level,board)]
        if selected:return selected,'teacher-curated'
    result=[]
    normalized={'PUC1':'1st','PUC2':'2nd'}[level]
    for path in Path(settings.QUESTION_PAPERS_DIR).rglob('*.pdf'):
        if infer_subject_level(path)!=(subject,normalized,board.lower()):continue
        lower=path.name.lower()
        # Exclude question banks and answer keys from recurrence counts.
        if any(tag in lower for tag in ('_qb','_sov','question_bank')):continue
        years=re.findall(r'20\d{2}',path.name)
        if not years:continue
        try:
            for page_number,page in enumerate(PdfReader(path).pages,1):
                text=page.extract_text() or ''
                matches=list(re.finditer(r'(?m)^\s*(\d{1,3})[.)]\s+',text))
                for i,match in enumerate(matches):
                    body=text[match.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
                    if len(body)<15:continue
                    mark=re.search(r'(?:\[|\()\s*(\d{1,2})\s*(?:marks?)?\s*[\])]|(\d{1,2})\s*marks?\b',body,re.I)
                    result.append({'subject':subject,'level':level,'board':board,'year':int(years[0]),'text':body[:4000],
                                   'marks':int(next(g for g in mark.groups() if g)) if mark else None,
                                   'source':path.name,'page':page_number,'topic':None,'verified':False})
        except Exception:continue
    return result,'automatic PDF extraction (unreviewed)'

def trend_report(records,current_year=None):
    end=current_year or date.today().year
    window=list(range(end-4,end+1))
    records=[r for r in records if r['year'] in window]
    unique={}
    for r in records:unique[(r['source'],r['year'],' '.join(r['text'].split()))]=r
    records=list(unique.values())
    counts=[Counter(words(r['text'])) for r in records]
    df=Counter(w for counter in counts for w in counter)
    ranked=Counter()
    for counter in counts:
        total=sum(counter.values()) or 1
        for word,n in counter.items():ranked[word]+=(n/total)*(math.log((1+len(records))/(1+df[word]))+1)
    topics=[]
    explicit=sorted({r.get('topic') for r in records if r.get('topic')})
    terms=explicit if explicit else [word for word,_ in ranked.most_common(15)]
    for term in terms:
        matches=[r for r in records if r.get('topic')==term] if explicit else [r for r in records if term in words(r['text'])]
        topics.append({'topic':term,'question_count':len(matches),'years':sorted({r['year'] for r in matches}),
                       'known_marks':sum(r.get('marks') or 0 for r in matches),'tfidf_score':round(ranked.get(term,0),4)})
    topics.sort(key=lambda t:t['question_count'],reverse=True)
    distribution=Counter('unknown' if r.get('marks') is None else 'short' if r['marks']<=2 else 'mid' if r['marks']<=5 else 'long' for r in records)
    available=sorted({r['year'] for r in records})
    return {'window':window,'available_years':available,'missing_years':[y for y in window if y not in available],
            'question_count':len(records),'topics':topics,'mark_distribution':dict(distribution),
            'sources':sorted({r['source'] for r in records}), 'verified':bool(records) and all(r.get('verified',False) for r in records)}

def analyze(subject,level,board):
    records,origin=question_records(subject,level,board)
    report=trend_report(records)
    # Blocks are joined with a blank line between them, but a markdown table
    # only parses when its rows sit on consecutive lines.
    lines=['## Previous-year question analysis','',f"Dataset: {origin}. Questions: {report['question_count']}.",'',
           f"Available years: {', '.join(map(str,report['available_years'])) or 'none'}.",'',
           f"Missing years in the five-year window: {', '.join(map(str,report['missing_years'])) or 'none'}."]
    if not report['verified']:lines+=['','Automatic extraction and keyword topics require teacher review before drawing exam predictions.']
    if report['topics']:
        lines+=['','| Topic / keyword | Questions | Years | Known marks |','|---|---:|---|---:|']
        lines += [f"| {t['topic']} | {t['question_count']} | {', '.join(map(str,t['years']))} | {t['known_marks']} |" for t in report['topics']]
    else:lines+=['','No usable questions found. Add teacher-curated question records or readable question papers.']
    lines+=['','Mark distribution: '+json.dumps(report['mark_distribution'])]
    return {'analysis':'\n'.join(lines),'report':report}
