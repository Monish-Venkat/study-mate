# StudyMate — Project Summary

A curriculum-grounded teaching assistant for Karnataka PUC and CBSE students, built on
**Corrective Retrieval-Augmented Generation** with persona-conditioned explanation.

---

## 1. The problem

Four constraints converge in Indian pre-university classrooms:

| Constraint | Consequence |
|---|---|
| ~100:1 student-to-faculty ratio | personalised help is unavailable outside class hours |
| General chatbots know no syllabus | confident answers about the wrong course |
| Board-specific exam formats | generic answers earn generic marks |
| Previous-year papers sit unmined | students guess at what will be asked |

A general LLM solves none of these. Plain RAG solves only the first two, and only partly.

---

## 2. Why plain RAG is not enough — the core technical argument

This is the heart of the project and the strongest thing to present.

Vector retrieval ranks passages by **cosine similarity**, which is a proxy for relevance,
not relevance itself. A passage can sit close to the query in embedding space and still
fail to answer it.

**Demonstrated failure in this project:** asking for a physics practice paper retrieved the
textbook's *preface and contents pages*, because those pages contain the word "physics"
more densely than any chapter does. The generated paper asked students to *"list five
chapter titles"* and *"explain the purpose of the box items in the preface."* Retrieval
succeeded by its own metric and failed completely at the task.

**The fix is a corrective loop, not a better embedding.**

### Corrective RAG pipeline (`app/services/crag.py`)

```
query → retrieve (top-k, metadata-filtered)
      → GRADE each passage for actual support  (LLM evaluator, 0.0 / 0.5 / 1.0)
      → decide:
           CORRECT    strong evidence     → answer from graded passages
           AMBIGUOUS  partial evidence    → rewrite query, re-retrieve, merge
           INCORRECT  no usable evidence  → rewrite; if still nothing, abstain
      → generate with board-aware prompt
```

Adapted from Yan et al., *Corrective Retrieval-Augmented Generation* (2024).

**Measured effect.** On a wave-optics question the grader kept 2 of 5 retrieved passages;
on a refraction question it kept 1 of 5. The discarded passages were front matter. Answer
latency also **fell from ~53s to ~11s**, because the model reasons over less noise.

Every answer returns its retrieval telemetry, so grounding is inspectable rather than
assumed:

```json
{"enabled": true, "retrieved": 5, "action": "correct",
 "dropped": 3, "best_grade": 1.0, "rewritten_query": null}
```

---

## 3. Board-aware generation

Interpolating `Board=KA` into a prompt tells a model nothing. Each board now carries its
actual examination conventions (`app/core/prompts.py`):

- **Karnataka PUC** — 1/2/3/5 mark structure; 5-mark items expect a derivation, labelled
  diagram or numerical; marks awarded per visible step, so steps must be shown.
- **CBSE** — stepwise value-point marking, competency-based and assertion-reason items;
  each value point must appear separately.

Answers are required to follow the shape a marking scheme rewards: direct answer →
explanation in textbook terminology → formula with symbols and SI units defined → worked
example. Evidence is cited inline as `[1]`, `[2]`, and the model must state which part of a
question the retrieved material does **not** cover rather than filling it from memory.

---

## 4. Twelve modules

| # | Module | Status |
|---|---|---|
| 1 | Data pipeline & vector store — FAISS, MiniLM, 7,669 chunks | working |
| 2 | FastAPI backend & router — 21 endpoints | working |
| 3 | Telegram bot interface | implemented, needs bot token |
| 4 | PYQ trend engine — TF-IDF over 102 extracted questions | working |
| 5 | Bloom's mock paper generator — blueprint-validated | working |
| 6 | Study planner — subtopic-level, source-grounded | working |
| 7 | Dialogue memory — per-topic scores, weak-topic tracking | working |
| 8 | Voice I/O — Whisper STT; gTTS opt-in | STT working |
| 9 | Teacher dashboard — analytics API, key-gated | working |
| 10 | Security — AES-256-GCM at rest, HMAC-SHA256 identities | working |
| 11 | Adaptive pedagogy — strategy selected from performance | working |
| 12 | YouTube persona engine — style fingerprint from transcripts | working |
| **+** | **Corrective RAG layer** | **working** |

---

## 5. Novelty claims, in defensible order

1. **Corrective RAG in an educational setting.** Retrieval grading, query rewriting and
   abstention applied to curriculum QA, with a reproducible failure case (front-matter
   pollution) that plain RAG does not survive.
2. **Board-conditioned generation.** Answer structure derived from the marking scheme of a
   specific examination board, not a generic "explain this" prompt.
3. **Persona-conditioned explanation.** A YouTube educator's teaching style is distilled
   into a five-field fingerprint from 360 transcript passages and used to condition
   phrasing while facts stay bound to institutional material.
4. **PYQ-seeded paper generation.** Practice papers retrieve against recurring exam topics
   mined from past papers, tying Module 5 to Module 4 rather than to a bare subject name.
5. **Hybrid inference routing.** Per-task model selection — local Qwen for tutoring,
   Vertex Gemini for structured generation — chosen by capability, with privacy kept for
   the conversational path.

---

## 6. Evidence to show

| Claim | Evidence |
|---|---|
| Answers are grounded | inline `[1][2]` citations resolving to file + page |
| Retrieval is corrected, not trusted | telemetry shows 3 of 5 passages dropped |
| Papers are curriculum-real | 15/15 physics questions after the PYQ-seeding fix, 0/15 before |
| Planner is not hardcoded | subtopics: *wavefronts and their propagation; principle of superposition; polarization of light* |
| Persona is derived, not asserted | fingerprint correctly identifies Hindi–English code-switching |
| System is exercised | 21 endpoints tested; validation, auth-gating and abstention all verified |

---

## 7. Honest limitations — state these before you are asked

Naming these is a strength in a viva, not a weakness.

- **Cross-lingual persona does not fire.** `all-MiniLM-L6-v2` is English-trained, so a
  Hindi-caption educator never clears the five-passage relevance floor against an English
  corpus. The safety fallback engages correctly. A multilingual encoder is required.
- **Model capability is a faithfulness issue, not just speed.** Asked to derive `F = ma`,
  the local 3B model produced Snell's law that was **not in the retrieved context** —
  correct physics, ungrounded. Gemini abstained on the same gap. This is what a RAGAS
  faithfulness metric would penalise.
- **Sub-5-second latency is unattainable** for a local 7B model on a 4 GB GPU (~6.5 tok/s).
  The 3B model fits and reaches ~19.6 tok/s but cannot emit valid blueprint JSON.
- **Corpus is partial.** 102 PYQ questions from one year; syllabus coverage incomplete.
- **Evaluation is a protocol, not results.** RAGAS/PSC/TAM thresholds are defined; the
  cohort study has not been run.

---

## 8. Running it

```bash
ollama serve                                              # terminal 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # terminal 2
cd frontend && npm run dev                                # terminal 3
```

Open http://127.0.0.1:3000

Model routing lives in `.env`; prefix any model with `vertex:` or `ollama:` to route that
tool independently. `ENABLE_CRAG=false` disables the corrective layer for A/B comparison —
useful live, as it shows the ungraded passages returning.

---

## 9. The one-sentence pitch

> StudyMate treats retrieval as something to be **verified rather than trusted**: every
> passage is graded for whether it actually supports the question, weak retrieval triggers
> query rewriting, and unanswerable questions are declined rather than answered from the
> model's memory — then the grounded answer is shaped to the marking scheme of the
> student's own examination board, optionally in the voice of a teacher they already follow.
