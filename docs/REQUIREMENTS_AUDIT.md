# Research requirements audit

Source: ieee_paper.pdf, “StudyMate: An Adaptive RAG Teaching Assistant with YouTube Persona-Driven Explanation for Students”, especially Sections IV–VI and Tables II–III. Reviewed 6 September 2026. The paper is a design-and-architecture contribution: its acceptance thresholds are targets, not measured results.

## Subsequent Module 12 implementation

The user subsequently requested implementation of the YouTube persona engine. It now supports registration, accessible captions and pasted text, timestamped token chunks, persistent SQLite transcript vectors, validated cached style descriptors, top-three conditioning after a five-relevant-passage gate, and frontend selection. See [YOUTUBE_PERSONA.md](YOUTUBE_PERSONA.md). This is a local-stack implementation, not the paper's Qdrant/MongoDB architecture; live Ollama generation and PSC evaluation remain unverified. The original audit below records the earlier baseline except for the updated Module 12 row.

## Overall verdict

**Not all requirements are implemented.** The original code was a partial PUC RAG prototype with startup, configuration, ingestion, and retrieval defects. This delivery repairs the core prototype and adds a working Next.js guest interface. It does not implement the paper's entire twelve-module architecture or establish its research claims.

The user confirmed that the interface should retain current PUC subjects, despite the paper's engineering-semester scope. The root `app/` is now the maintained backend. The nested `edurag_fixed_full/` copy was inspected and left as a legacy snapshot; do not launch from that folder.

## Module-by-module assessment after repairs

| Paper requirement | Status | Repository evidence and remaining work |
|---|---|---|
| 1. Four Qdrant collections, HNSW, MiniLM, paragraph/token chunking, metadata | Partial; different architecture | `app/services/ingest.py`, `embeddings.py`, `faiss_store.py`: MiniLM interface and FAISS flat inner-product index. Repaired index scanning, page references, filename metadata, duplicate-path skipping, and subject/year/board/type filtering. No Qdrant collections, HNSW, transcript store, or token-aware recursive splitter. Existing chunking remains 700 characters/120 overlap, not paper's 500/50 tokens. |
| 2. FastAPI command backend with eight routes and LangChain | Partial | Restored missing root `app/main.py`. Five study routes and health work; Next.js uses an allowlisted same-origin proxy. No LangChain, planner, teacher, persona, or voice routes. `/summary` and `/mock-paper` differ from paper's `/rev` and `/mock`. |
| 3. Telegram bot, commands, group and private delivery | Missing | Existing `app/routers/telegram.py` returns a fixed placeholder and never dispatches or sends a message. It is deliberately not exposed by the repaired app. No bot-token configuration or real bot integration. |
| 4. Five-year TF-IDF PYQ frequencies and mark distribution | Partial prototype only | `/pyq` now retrieves only matching question-paper excerpts. It prompts an LLM to review a limited selection; no all-paper TF-IDF, question parsing, mark extraction, or validated five-year statistics. UI explicitly calls this a past-paper review. |
| 5. Bloom-graded mocks with internal choice and historical format | Partial | Prompt now requests Bloom tiers, per-question marks, equal-mark alternatives and the requested total. No structured output validator, mark-total enforcement, historical pattern calibration, or measured format compliance. UI labels generated material as practice. |
| 6. Exam-aware study planner and score-driven rescheduling | Missing | No scheduling, exam-date extraction, score vectors, syllabus allocation, or mock-score update pipeline. |
| 7. MongoDB persistent ten-turn dialogue and learner profile | Missing as specified | `memory.py` is an in-process dictionary. `/ask` saves messages but never injects them into future prompts. No durable memory, timestamps, language/persona preferences, or score profile. Browser session results are convenience history, not contextual dialogue memory. |
| 8. Whisper/gTTS bilingual voice | Missing | No OGG upload, transcription, language detection, synthesis or audio delivery. |
| 9. Teacher analytics and runtime uploads | Missing | No Streamlit dashboard, confusion heatmap, score distribution, syllabus coverage, faculty upload, or persona analytics. Guest student UI is not a teacher dashboard. |
| 10. Hashed identifiers, AES-256, retention, encrypted delivery | Missing as specified | Frontend generates anonymous random IDs, but this is not encryption or authentication. No AES storage, retention enforcement, or verified encrypted transport. Current local app is for development; do not claim paper-level security. |
| 11. Adaptive pedagogy from performance and history | Partial | Student can manually select guided learning or summaries. No automatic strategy selection using scores, clarification counts, language, or dialogue. |
| 12. YouTube Transcript Persona Engine | Implemented locally; evaluation pending | Added educator registration, caption/paste ingestion, 300/50 tokenizer windows, timestamp metadata, up-to-30-passage fingerprinting, cached descriptors, top-3 style retrieval after a five-match gate, and persona-conditioned tutoring. SQLite/exact cosine substitutes for MongoDB/Qdrant. Real generation and PSC still need validation. See `docs/YOUTUBE_PERSONA.md`. |
| Hallucination controls | Partial, improved | Added configurable similarity cutoff (0.30 is an uncalibrated development default), no-evidence abstention without LLM calls, grounding instruction across modes, source/page listing, and citation instructions. Source listing does not prove individual claims are supported. No RAGAS screening or teacher correction loop. |
| Ollama Qwen2.5-7B | Code aligned; runtime unverified | Removed hard-coded 3B override; defaults now use `qwen2.5:7b` per configured role. Real failures return HTTP 503, and 404/405 native endpoint failures try the compatible endpoint. Model pull and inference remain to be run. |
| Docker/AWS deployment | Missing | No container configuration or deployment evidence. |

## Original defects repaired

- README pointed to missing root `app.main`; restored a usable FastAPI entry point.
- Settings referenced by ingestion and RAG were absent; added chunk, model and similarity settings.
- Build script previously only made directories; now scans PDFs, indexes text and reports failures. `--dry-run` and `--limit` support inventory and bounded checks.
- Root FAISS store ignored `VECTOR_DIR`; now honors configuration.
- Retrieval ignored selected course and source type; now filters before selecting top-k.
- Empty/weak retrieval previously went to generation; now abstains.
- LLM ignored selected model and returned service failures as successful answers; fixed both.
- Ingestion lost page references and mislabeled question-paper metadata; added page/year metadata and inference for the supplied naming layout.
- Chemistry files named `kech*` inside mathematics now index as chemistry. Files were not moved.
- Added bounded request validation and a responsive Next.js interface with all five available tools, error/loading/cancellation states, session results, Markdown, copy and download.

## Data limitations

The root dataset contains 95 PDFs. It covers PUC physics, chemistry, mathematics and biology, not the engineering-semester corpus described in the paper. Supplied question-paper filenames span 2024–2026; model question papers, question banks and schemes of valuation are mixed with exam papers. They must be curated and classified before claiming five-year exam trends. No official syllabus PDFs or YouTube transcripts are present. A CBSE directory is not evidence of a CBSE corpus; current ingestion defaults unlabelled supplied sources to Karnataka.

`data/vectors/edurag.db` is a different store from the configured FAISS files. Its existence does not make this FAISS backend ready. Before this delivery there was no `index.faiss`/`meta.jsonl` pair at the configured location. Health now exposes this distinction.

The filename level inference is specific to the supplied PUC archive (puc-1 is first year; other question-paper filenames are treated as second year). Review metadata when adding new files. Duplicate detection uses source paths; changing a PDF requires building into a fresh `VECTOR_DIR`. Scanned PDFs need OCR, which is not implemented. Chapter input augments semantic retrieval; there is no exact chapter metadata filter.

## Evaluation evidence still required

No benchmark dataset, faculty labels, participant survey, or recorded results were supplied. None of these thresholds can be marked achieved from code inspection or unit tests:

| Metric | Paper target | Evidence needed |
|---|---|---|
| Faculty domain accuracy | >=85% | Faculty-rated answers |
| RAGAS faithfulness | >=0.85 | Evaluator outputs over approved benchmark |
| Answer relevance | >=0.80 | Evaluator outputs |
| Context relevance | >=0.75 | Relevant-passage judgments |
| Persona consistency | >=0.78 | Genuine and neutral excerpts plus independent style judgments |
| TAM usefulness/ease of use | Both >=4/5 | At least 30 respondents after at least two weeks |
| Latency | <5 seconds | Timed real inference with hardware and workload recorded |
| PYQ trend accuracy | >=80% | Annotated five-year ground truth |
| Mock format compliance | >=90% | Faculty-reviewed format checks |
| Multilingual ASR WER | <=15% | Labelled bilingual recordings and transcripts |

Paper review points: clarify the relationship between top-3 persona retrieval and the five-matching-passage gate; specify whether chunk sizes are tokens or characters; reconcile session-limited retention with persistent dialogue; verify the Telegram security and YouTube caption-access assumptions against actual APIs before implementation. Local-inference privacy claims must also account for hosted memory and external services. These are design questions, not functionality verified here.

## Completion priority

1. Install the embedding model, build a curated index, run Ollama, and validate grounded answers with faculty.
2. Validate the implemented persona module with real educator lectures, tune the coverage threshold, and evaluate PSC.
3. Implement actual five-year question parsing/statistics, validated mocks, planner and persistent contextual memory.
4. Add Telegram delivery, voice, teacher analytics, adaptive strategy and verified security controls.
5. Run and report the evaluation protocol. Keep the paper framed as proposed architecture until evidence exists.
