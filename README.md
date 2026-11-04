# StudyMate: PUC study workspace

A simple **Next.js frontend with no login or signup**, connected to the FastAPI/Ollama backend. Tools: questions, guided learning, revision notes, past-paper excerpt review, and practice papers.

The research architecture is not fully implemented. See [the requirements audit](docs/REQUIREMENTS_AUDIT.md) for all twelve modules, repaired defects, dataset gaps, and evaluation targets. Use this root project; `edurag_fixed_full/` is a legacy copy and is not the maintained app.

## Start the backend

Use Python 3.11+ and run these commands from this folder:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen2.5:7b
```

Keep Ollama running (`ollama serve` if needed). Inspect the dataset and then build the real index:

```powershell
.venv\Scripts\python scripts/build_index.py --dry-run
.venv\Scripts\python scripts/build_index.py
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first index build downloads MiniLM and embeds the PDFs; it can take time. `--limit 1` runs a small indexing smoke test. Reruns skip existing source paths. To reindex modified PDFs, set `VECTOR_DIR` to a fresh directory and build again. Restart the backend after indexing. Text extraction does not perform OCR.

The supplied `data/vectors/edurag.db` is not the FAISS index used by this code. A healthy API with an empty index will return an honest no-evidence response, not a generated answer.

## Start the frontend

Use Node.js 20.9+ in a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:3000. No account is needed. The server-side proxy connects to `http://127.0.0.1:8000`; override `BACKEND_URL` in `frontend/.env.local` if necessary. All API calls stay on the same browser origin.

For a production build: `npm run build`, then `npm start`. These commands bind locally. Internet deployment, authentication, encrypted storage, and rate limiting are outside this prototype's implemented scope.

## Data layout

- `data/textbooks/{physics,chemistry,mathematics,biology}/{1st,2nd}`
- `data/question_papers` (root PDFs and board subdirectories are scanned)
- `data/syllabus` (currently no syllabus corpus supplied)
- `data/db/faiss` (generated index; configurable)

The frontend keeps the current PUC subjects as requested. Supplied sources default to Karnataka when no board folder is present. CBSE may return no evidence. Chemistry PDFs with `kech` filenames are classified as chemistry even when stored in the mathematics folder.

## Verification

```powershell
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest tests -q --basetemp tmp/pytest-local
cd frontend
npm run typecheck
npm run build
npx playwright install chromium
```

With the backend and production frontend running, execute `node tests/browser-smoke.mjs` from `frontend`. It checks live empty-index integration and mocked successful/error responses, all five tool payloads, mobile overflow, and download behavior. Test responses are labelled fixtures and are not research results.

See `docs/VALIDATION.md` for the actual checks performed. Generated answer quality, complete corpus indexing, latency and research acceptance targets remain unverified until the model/data setup and evaluation are completed.

## YouTube teaching personas

The frontend now includes **YouTube persona**. Register a lecture URL, import available captions (or paste transcript text), inspect the cached teaching-style profile, and select it for Ask, Guided learning or Revision. See [persona setup and implementation](docs/YOUTUBE_PERSONA.md). The style layer requires Ollama, MiniLM, enough relevant transcript passages, and factual course evidence.
