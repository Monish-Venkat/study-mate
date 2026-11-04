# Validation record

Date: 6 September 2026.

## Passed

- Next.js 16.3.4 production build, including TypeScript checks and route generation.
- 11 Python regression tests in `tests/test_backend.py`: all five API response contracts on empty retrieval, request validation, FAISS filter-before-top-k and persistence, metadata correction, chunk validation, weak-evidence gating, citations, model service HTTP 503, compatible-endpoint fallback and configured model selection.
- Dataset inventory: 95 root PDFs found by `scripts/build_index.py --dry-run`.
- Browser smoke test against production Next.js at localhost:3000 and FastAPI at localhost:8000: live empty-index response, all five request payloads, fixture Markdown rendering, clipboard, text download, 503 recovery, clear history, mobile overflow, absence of login/signup, and no browser runtime errors.
- Desktop 1440px and mobile 390px screenshots reviewed for clipped content and layout problems. Navigation scrolls horizontally on mobile; page itself has no horizontal overflow.
- npm dependency audit at installation: zero reported vulnerabilities.

## Limits

No full MiniLM embedding/index run or live Ollama generation was performed. Ollama is not installed on the available command path and no ready FAISS corpus was supplied. Success-path browser answers and model HTTP tests use explicit test fixtures; they do not validate educational accuracy or model quality. Empty-index integration was real.

The Python test run used project-local dependencies under `.runtime/python` and an explicit temporary folder because the system Python command and sandboxed package access were unavailable. README provides ordinary virtual-environment setup. Two upstream deprecation warnings from FastAPI/Starlette's httpx test adapter were present; all tests passed.

No RAGAS/PSC/TAM results, security verification, TF-IDF accuracy, mock format compliance, voice WER, or five-second latency claim is established by these checks.

## Independent interface review

A separate bounded reviewer inspected the implementation and both screenshots. Verdict: **Pass for the requested frontend scope**. No material visual or functional fixes were requested. The reviewer did not certify live generation or research targets.

## Module 12 follow-up validation

The YouTube persona implementation passes the production Next.js build and TypeScript checking. Expanded Python suite: **25 passed**. Added coverage includes video-URL validation, 300/50 token windows, timestamp metadata, distributed sampling, persistent registration, duplicate handling, failed-import retry, restart recovery, validated profiles, subject isolation, relevance gating, top-three style references, and persona-to-RAG integration.

The first persona browser run verified the live empty educator list and invalid-URL rejection, then exercised fixture registration. It stopped at a test locator that matched select labels too strictly. That locator was corrected, but the rerun was blocked by automatic approval review reporting exhausted workspace credits. The full persona browser test is therefore **not recorded as passed**. Run `node tests/persona-smoke.mjs` from `frontend` once browser execution is available.

The transcript and sentence-transformer dependencies were installed. A real MiniLM smoke test was not executed, and Ollama was confirmed unreachable at port 11434. No successful live caption import, style fingerprint, persona answer or PSC result is claimed. Backend success tests use isolated fixture transcripts, vectors and model responses.
