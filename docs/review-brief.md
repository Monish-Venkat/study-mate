# Review brief

What StudyMate is, what is worth leading with, and how the hard problems were
broken open. Every figure here was measured against the running system; the
screen-by-screen demo script is in [review-demo.md](review-demo.md) and the
screenshots are in [screenshots/](screenshots/README.md).

## What it is, in one breath

A retrieval-augmented tutor for Karnataka 1st and 2nd PUC students that answers
**only from the prescribed textbooks** — 8,191 indexed chunks — and shows the
page behind every claim. Six tools over one grounded pipeline: ask a question,
guided learning, revision notes, past-paper review, practice paper, study map.
Plus a teacher dashboard and a Telegram bot. It runs entirely on local models,
so a school needs no cloud account and no student data leaves the machine.

## The points worth leading with

**1. Grounding is enforced, not promised.** Every answer is audited
statement-by-statement against the retrieved passages, and the UI shows the
fraction that traces back — 0.86 on the physics derivation, 100% on the biology
one. Most student RAG projects claim grounding; this one displays it and can be
checked live.

**2. The real textbook figure, not a generated one.** 522 figures extracted
from the PDFs with captions and page numbers. Asked to draw the fluid mosaic
model, it returns **Figure 8.4 from kebo108.pdf, page 9**. Drawing a diagram is
where generative tutors are weakest; retrieving the real one sidesteps it.

**3. A feature was measured and then switched off.** The abstention gate was
built so thin retrieval refuses rather than guesses, then benchmarked — and
**no threshold caught bad answers without falsely refusing good ones**. It ships
off by default with the numbers recorded in `app/core/config.py`. A negative
result, kept and explained.

**4. The limit of our own metric is known.** `grounded_fraction` measures
*traceability, not truth*. An answer scored 0.83 while wrongly stating Euglena
has two flagella, and a Hindi answer scored **1.0** because the audit matches
against English passages and cannot read Devanagari. If a panellist asks
whether grounded means correct, the honest answer is already prepared.

**5. Multilingual support is refused rather than faked.** Eight languages in
the selector; the local models produce confident nonsense in all of them. A
Hindi request therefore answers in English **with an explicit notice**, and the
capable-model hook (`LLM_MULTILINGUAL_MODEL`) is one environment variable away.

**6. Corrective RAG, properly cited.** Hybrid dense + BM25 retrieval fused by
Reciprocal Rank Fusion, then CORRECT / AMBIGUOUS / INCORRECT grading with
recovery, following Yan et al. 2024.

**7. Privacy and roles.** No student accounts. Teacher analytics are aggregated
and key-gated — 403 without the key, 200 with it — and the 30-day retention is
stated in the interface.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, Python |
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript |
| Retrieval | FAISS `IndexFlatIP` dense + BM25 lexical, fused by RRF |
| Models | Ollama — `qwen2.5:3b` (tutoring), `qwen2.5:7b` (paper generation), local |
| Figures | pypdf extraction, caption parsing, content-hash ids |
| Mathematics | remark-math to rehype-katex to KaTeX |
| Diagrams | Mermaid |
| Verification | Playwright (57 screenshots), an 11-surface smoke sweep, a benchmark harness |
| Delivery | Telegram webhook with an HMAC-validated secret |

## Dead ends, and how each broke open

**Answers looped — sixty bullets repeating the same five points.** Prompt rules
did not hold, because a prompt is advice. The fix went into code:
`answer_text.drop_repeats` guarantees no repeated list item reaches a student.
That fix then deleted a real lens-maker step whose symbols were primed (`v'`
against `v`), so items containing mathematics now compare by exact equality
only. The fix breaking something was caught before it shipped.

**The response-language selector did nothing.** The root cause was not a faulty
handler: **no prompt builder ever read it.** Fixing that exposed the deeper
problem — the models cannot write those languages — which produced the
honest-refusal design above.

**The practice paper was dead on the local model.** Three failures stacked
behind one another, each visible only once the one in front was fixed:

- it wrote **LaTeX inside JSON strings** (`\frac`), which is not a legal escape,
  so the parser discarded complete and correct papers. Asking it in the prompt
  to stop did not work. The constraint moved from the prompt to the sampler:
  Ollama's constrained JSON decoding makes invalid output unrepresentable
- it **skipped blueprint slots** sharing the same marks and Bloom level,
  returning ids 1, 2, 3, 7 of 8. Fixed by naming every required id and capping
  answer length so the run finishes
- a **surplus internal choice** rejected the whole paper. The blueprint is the
  authority on structure, so the extra field is now dropped rather than eight
  good questions dying for an eighth's extra field

The result is a validated 8-question, 35-mark paper generated locally in about
six minutes, at roughly 5.6 tokens per second.

**The paper worked under `curl` and failed in the browser at exactly 5.1
minutes.** Node's `fetch` is undici, whose `headersTimeout` defaults to **300
seconds and silently ignores the `AbortSignal`**, so the 15-minute timeout was
never in effect. The backend sends no response headers until the paper is
finished, so the proxy hung up while the backend carried on and completed it.
The study route now uses `node:http`, which imposes no header deadline. Found
only by driving the real interface — the API sweep passed throughout.

**One malformed formula could swallow a whole answer.** A biology answer drew
the membrane with a LaTeX `array` environment; KaTeX could not parse it, and
the unbalanced `$$` consumed everything after it — including the sources line —
into a single red block. Fixed at both ends: the prompt forbids LaTeX
environments, and the renderer drops an unmatched delimiter so one bad formula
costs only its own formatting.

**A figure plate repeated its caption three times** under a note claiming the
panels were matched by position, which was no longer true. Panels are now
grouped under the single caption the book actually gives them, with an honest
line saying the book does not state which panel is which.

## Two things to control on the day

Generate the practice paper **before** the panel is watching: five to eight
minutes on this CPU.

Demo personas with **Walter Lewin and "Explain electric flux and Gauss law"**.
The style is applied only when at least five transcript passages match, and the
Hindi lecture persona returns `applied=False` even on its own topic. Both
educators are registered under Physics, so on any other subject the dropdown is
correctly empty.

Avoid the human-heart question — it scores 0.82 but the crops are page
fragments — and avoid mathematics diagrams, where only 5 figures exist and three
are chapter title pages. The four safe biology figures and the convex-lens ray
diagram are listed in [review-demo.md](review-demo.md).
