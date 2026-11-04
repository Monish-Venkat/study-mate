"""Register a YouTube lecture as a teaching persona from a caption excerpt.

The persona engine caps a transcript at 100,000 embedding tokens. Long lectures
exceed that, so this fetches the real captions and submits the leading portion
through the supported paste-transcript path (recorded with origin="pasted").
"""
import argparse
import json
import urllib.request

from youtube_transcript_api import YouTubeTranscriptApi

from app.services.embeddings import get_model

TOKEN_BUDGET = 90000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('video_id')
    parser.add_argument('--name', required=True)
    parser.add_argument('--subject', default='physics')
    parser.add_argument('--language', default='en')
    parser.add_argument('--title', default='')
    parser.add_argument('--api', default='http://127.0.0.1:8000')
    args = parser.parse_args()

    segments = YouTubeTranscriptApi().fetch(args.video_id, languages=[args.language])
    tokenizer = get_model().tokenizer

    kept, total = [], 0
    for segment in segments:
        count = len(tokenizer.encode(segment.text, add_special_tokens=False))
        if total + count > TOKEN_BUDGET:
            break
        kept.append(segment.text)
        total += count

    excerpt = ' '.join(kept)
    print(f'kept {len(kept)}/{len(segments)} caption segments, ~{total} tokens, {len(excerpt)} chars')

    payload = json.dumps({
        'name': args.name,
        'subject': args.subject,
        'url': f'https://www.youtube.com/watch?v={args.video_id}',
        'title': args.title or f'Lecture {args.video_id} (opening excerpt)',
        'language': args.language,
        'transcript': excerpt,
    }).encode()

    request = urllib.request.Request(f'{args.api}/personas/', data=payload,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=300) as response:
        print('register:', response.read().decode())


if __name__ == '__main__':
    main()
