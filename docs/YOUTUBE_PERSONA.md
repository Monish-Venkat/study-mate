# YouTube teaching persona engine

Module 12 now has a local implementation in `app/services/persona.py`, `persona_store.py`, `app/routers/persona.py`, and `frontend/app/persona-panel.tsx`.

## Use it

1. Start Ollama with `qwen2.5:7b` available. Install the updated `requirements.txt` and start the backend.
2. Open the frontend. The **YouTube persona** navigation item takes you to the panel above the study form.
3. Choose the course subject, expand **Add a YouTube lecture**, enter an educator name and a single video URL, and select the caption language.
4. Click **Import lecture**. The import runs in the background; the panel refreshes its status every four seconds. The first import may download MiniLM.
5. If captions cannot be retrieved, select **Paste a transcript instead of fetching captions** and provide lecture text you can access. Register the same failed video again to retry.
6. After import, inspect the educator's style profile and video status. Add more videos to the existing educator when coverage is insufficient.
7. Select the educator in **Teaching style** and use Ask, Guided learning, or Revision notes. Select **Standard StudyMate** to turn persona styling off. Changing subject resets the selection.

A course index is still required. Transcripts provide style examples, not a replacement textbook corpus. Past-paper review and mock generation do not use persona styling.

## Implemented behavior

- Strict YouTube video URL parsing; supports watch, youtu.be, shorts, embed and live URLs. Only the validated video ID is used for caption retrieval. No arbitrary remote URLs are fetched.
- Caption retrieval through `youtube-transcript-api` with bounded HTTP request timeouts. User-supplied transcript fallback is explicitly labelled and has no fabricated timestamps.
- Actual tokenizer-based 300-token windows with 50-token overlap. MiniLM vectors average normalized subwindow embeddings when the model's token limit is smaller than 300; no silent truncation of the stored passage.
- Dedicated SQLite educator, video and passage tables under `DB_DIR/personas.sqlite3`. Transcript vectors remain separate from factual course retrieval. Exact cosine retrieval is used for this local prototype.
- Samples up to 30 passages distributed across the educator corpus. Ollama generates five validated descriptor fields: sentence length, analogy use, transitions, vocabulary and teaching approach.
- Descriptor and passage updates commit atomically after successful embedding and fingerprinting. Failed imports remain retryable. Duplicate ready/processing videos are not indexed twice. Additional successful videos refresh the profile.
- Imports serialize in the local process. Restart marks interrupted imports as failed with a retry message. Run one backend worker; this is not a distributed job queue.
- At inference, at least five passages must meet `PERSONA_MIN_SIMILARITY` (default 0.30, not yet calibrated). Only the top three condition phrasing. Thin coverage, missing profiles or style retrieval failure falls back to standard tutoring.
- Course retrieval and abstention run first. No course evidence means no generated persona answer.
- Prompt separates untrusted style examples from factual course context, preserves the chosen tutoring task, and forbids claiming to be the educator or implying endorsement. UI reports whether style was applied and separates style reference links from factual citations.
- Educator library survives restarts. Selection is per browser page/session; no login is introduced. On this local guest deployment, profiles are shared across visitors to the same server.

## API

- `GET /personas/`: educator profiles, readiness, video status and counts (no raw transcripts or vectors).
- `POST /personas/`: educator name, subject, URL, optional title/educator_id/transcript and caption language. Returns 202 with educator/video IDs. Poll GET for completion.
- Optional `persona_id` on `/ask/`, `/socratic/`, `/summary/`. Responses include `persona.applied`, `reason`, and style sources when applied.
- Frontend forwards registration/listing through `/api/personas`.

## Differences from the research architecture

This implementation preserves the existing local stack: SQLite with separate transcript vectors instead of MongoDB/Qdrant; direct Python prompt assembly instead of LangChain. It implements persona registration, ingestion, fingerprinting, caching, conditioning and coverage fallback, but does not establish PSC >=0.78 or complete the paper's encryption, Telegram, dashboard or research evaluation requirements.

Automatic public-caption access can fail or be blocked by YouTube. The official YouTube Data API caption-download operation requires permission to edit the video, so an API key is not a universal caption downloader. This implementation uses the public-caption library where available and offers supplied text as a fallback; it does not bypass restricted access.

References: [YouTube captions.download](https://developers.google.com/youtube/v3/docs/captions/download), [youtube-transcript-api documentation](https://github.com/jdepoix/youtube-transcript-api).

No live educator profile or measured style-consistency result is bundled. Real fingerprinting and answers require a reachable Ollama model. Pasted transcripts are user-supplied and do not verify the lecturer's identity.
