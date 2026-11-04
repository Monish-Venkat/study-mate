"""Score one system configuration against the benchmark.

Only what can be measured without gold answers is scored here: abstention
behaviour, retrieval economy, citation rate and latency. Answer correctness
requires the teacher annotations in benchmark.json and is deliberately not
guessed at by an LLM judge, since the judge and the generator share blind spots.

    python evaluation/run_benchmark.py --label vanilla --limit 40
"""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:8000'
DECLINE = re.compile(r'could not find supporting passages|not covered in your course', re.I)
CITATION = re.compile(r'\[\d+(?:,\s*\d+)*\]')


def ask(item, timeout):
    body = json.dumps({'student_id': 'bench', 'subject': item['subject'], 'level': item['level'],
                       'board': item['board'], 'question': item['question']}).encode()
    request = urllib.request.Request(BASE + '/ask/', data=body,
                                     headers={'Content-Type': 'application/json'}, method='POST')
    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace')), time.time() - start
    except urllib.error.HTTPError as exc:
        return {'error': exc.read().decode('utf-8', 'replace')[:200]}, time.time() - start
    except Exception as exc:
        return {'error': f'{type(exc).__name__}: {exc}'}, time.time() - start


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--benchmark', default='evaluation/benchmark.json')
    parser.add_argument('--out-dir', default='evaluation/results')
    parser.add_argument('--limit', type=int, default=0, help='0 runs every item')
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()

    data = json.loads(Path(args.benchmark).read_text(encoding='utf-8'))
    items = data['items']
    if args.limit:
        answerable = [i for i in items if i['answerable']][:args.limit]
        unanswerable = [i for i in items if not i['answerable']][:max(4, args.limit // 5)]
        items = answerable + unanswerable

    rows = []
    for index, item in enumerate(items, 1):
        result, secs = ask(item, args.timeout)
        text = result.get('answer', '') or result.get('error', '')
        body = text.split('Retrieved sources')[0]
        declined = bool(DECLINE.search(text))
        rows.append({
            'id': item['id'], 'answerable': item['answerable'], 'declined': declined,
            'secs': round(secs, 1), 'chars': len(body),
            'citations': len(CITATION.findall(body)),
            'sources': len(re.findall(r'page \d+', text)),
            'retrieval': result.get('retrieval', {}),
            'grounding': {k: v for k, v in (result.get('grounding') or {}).items()
                          if k != 'claims'},
            'answer': body.strip(),
        })
        if index % 10 == 0 or index == len(items):
            print(f'  {index}/{len(items)}')

    answerable = [r for r in rows if r['answerable']]
    unanswerable = [r for r in rows if not r['answerable']]
    # Abstention treated as detection of unanswerable questions.
    true_pos = sum(1 for r in unanswerable if r['declined'])
    false_pos = sum(1 for r in answerable if r['declined'])
    precision = true_pos / (true_pos + false_pos) if (true_pos + false_pos) else 0.0
    recall = true_pos / len(unanswerable) if unanswerable else 0.0

    summary = {
        'label': args.label,
        'items': len(rows),
        'answered': len(answerable) - false_pos,
        'avg_secs': round(sum(r['secs'] for r in rows) / len(rows), 1),
        'avg_sources': round(sum(r['sources'] for r in rows) / len(rows), 2),
        'citation_rate': round(sum(1 for r in answerable if r['citations']) / max(len(answerable), 1), 3),
        'abstention_precision': round(precision, 3),
        'abstention_recall': round(recall, 3),
        'false_abstentions': false_pos,
        'avg_restored': round(sum(r['retrieval'].get('restored', 0) for r in rows) / len(rows), 2),
        'avg_dropped': round(sum(r['retrieval'].get('dropped', 0) for r in rows) / len(rows), 2),
        'avg_boilerplate_removed': round(
            sum(r['retrieval'].get('boilerplate_removed', 0) for r in rows) / len(rows), 2),
    }
    graded = [r for r in answerable
              if not r['declined'] and r['grounding'].get('counts')]
    if graded:
        summary.update({
            'grounding_items': len(graded),
            'avg_grounded_fraction': round(
                sum(r['grounding'].get('grounded_fraction', 0) for r in graded) / len(graded), 3),
            'avg_cited_fraction': round(
                sum(r['grounding'].get('cited_fraction', 0) for r in graded) / len(graded), 3),
            'answers_with_unsupported': sum(
                1 for r in graded if r['grounding']['counts'].get('unsupported', 0) > 0),
            'answers_with_dangling': sum(
                1 for r in graded if r['grounding'].get('dangling_citations')),
            'avg_claims': round(
                sum(sum(r['grounding']['counts'].values()) for r in graded) / len(graded), 1),
        })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'{args.label}.json'
    path.write_text(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=1),
                    encoding='utf-8')
    print(json.dumps(summary, indent=1))
    print(f'-> {path}')


if __name__ == '__main__':
    main()
