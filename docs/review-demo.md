# Demo guide for the review

Everything here was run against the live system. Where a figure is named, the
actual PNG was opened and looked at, not just its caption and score — the
caption being right is no guarantee the image under it is.

## State of the system: 11 of 11 surfaces pass

| Surface | | Evidence |
|---|---|---|
| health | PASS | 8,191 chunks indexed |
| Ask a question | PASS | 1,666 chars, 0.86 traceable |
| Ask in Hindi | PASS | English plus the notice, 0 Devanagari — see below |
| Guided learning | PASS | 963 chars |
| Revision notes | PASS | 1,747 chars |
| Past paper review | PASS | 2,123 chars |
| Practice paper | PASS | 8 questions, 35 marks, local model, 5m18s — see below |
| Study map | PASS | mermaid returned |
| Figure search | PASS | figures returned with page numbers |
| Personas | PASS | 2 of 2 ready |
| Persona applied to an answer | PASS | applied=True with the right pairing |
| Teacher dashboard | PASS | 403 without the key, 200 with it |

### The practice paper runs locally now, but it is slow

`LLM_MOCK_MODEL` was `vertex:google/gemini-2.5-flash` and the Google
credentials on this machine have expired. It is now `qwen2.5:7b`, so the
feature needs no cloud account — but a 35-mark paper takes **five to eight
minutes** on this CPU (measured at 5m18s and 7m23s on two runs), because the
model runs at roughly 5.6 tokens a second. **Generate the paper before the
review starts**, or you will be watching a spinner in front of the panel.

Three bugs had to be fixed before the local model could produce a paper at
all, and all three would have bitten Vertex too, just less often:

- the model wrote LaTeX inside the JSON strings (`rac`, `\(`), which is not
  a legal JSON escape, so the parser threw away a complete and correct paper.
  Generation now uses constrained JSON decoding, so the escaping is enforced at
  the sampler rather than requested in the prompt
- asked for eight questions it returned ids 1, 2, 3, 7 — it skips blueprint
  slots that share the same marks and Bloom level. The prompt now names every
  id it must return and caps answers at 80 words so the run finishes
- a surplus `alternative` on a question the blueprint gave no choice for used
  to reject the whole paper; it is now dropped, since the blueprint is the
  authority on structure

Verified end to end:

```bash
curl -s -X POST http://127.0.0.1:8000/mock-paper/ -H "Content-Type: application/json" -d "{\"student_id\":\"check\",\"subject\":\"physics\",\"level\":\"PUC2\",\"board\":\"KA\",\"total_marks\":35}" -m 1800
```

8 questions, 35 marks, `validated: true`, internal choice on question 3, 12
sources, maths in Unicode (`R₁/R₂ = R₃/R₄`).

**One caveat worth knowing before someone on the panel reads it.** The 80-word
cap keeps the model on track, but it makes the answer guide terse: question 3
is answered in two lines for five marks. The questions are good; the answer
key is thinner than a real one. If a panel member asks, that is a model-size
limit, not a design choice.

If you would rather have the fuller Vertex output, re-authenticate and set
`LLM_MOCK_MODEL` back to `vertex:google/gemini-2.5-flash`:

```bash
gcloud auth application-default login
```

## Two bugs found while screenshotting every screen

Both were found by driving the real UI, not by reading code, and both are
fixed. Screenshots of every screen and every option are in
[screenshots/](screenshots/).

**The practice paper could not finish in the browser.** It worked from `curl`
and failed in the UI at 5.1 minutes every time with "the study service could
not be reached", while the backend carried on and finished the paper. The
cause is that Node's `fetch` is undici, whose `headersTimeout` defaults to 300
seconds and ignores the `AbortSignal` the route sets: the backend sends no
response headers until the paper is complete, so the proxy hung up first. The
study route now uses `node:http`, which imposes no header deadline, so the
15-minute `STUDY_TIMEOUT_MS` is the only limit that applies. A 35-mark paper
now completes in the browser.

**A malformed formula could swallow the rest of an answer.** One biology answer
tried to draw the fluid mosaic model with a LaTeX `array` environment. KaTeX
cannot parse it, so it rendered as red raw LaTeX — and because the `$$`
delimiters were unbalanced, everything after it, including the retrieved
sources line, was consumed into the same red block. Two changes: the prompt now
forbids LaTeX environments outright, and the renderer drops an unmatched `$$`
or `$` so one bad formula costs only its own formatting. Nine cases cover it,
including that a balanced formula and an escaped `\$` are untouched.

## Start the three services

```bash
ollama serve
```

```bash
cd study-mate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd study-mate/frontend && npm run dev
```

Ollama is the one that quietly dies; when it does, every tool returns
`503 The local language model is unavailable` while the page still shows
"Index ready", because the index is loaded and the model is not. Check it
first if anything 503s:

```bash
curl -s http://127.0.0.1:11434/api/tags
```

## Questions that show a good diagram

These four return a clean, completely labelled textbook figure. Set the
subject and year exactly as listed — the index filters on both.

| Subject / year | Ask | Shows |
|---|---|---|
| Biology 1st PUC | Draw the fluid mosaic model of the plasma membrane | Figure 8.4, score 0.93 |
| Biology 1st PUC | Draw a labelled diagram of a neuron | Figure 18.1 — dendrites, myelin sheath, node of Ranvier, synaptic knob |
| Biology 1st PUC | Draw a labelled diagram of T.S. of a dicot stem | Figure 6.4, dicot and monocot side by side |
| Physics 2nd PUC | Draw a ray diagram for a convex lens | FIGURE 9.17 — object, F, F', image, fully labelled |

## Do not demo the human heart

"Draw a labelled diagram of the human heart" scores **0.82**, which looks like
the strongest possible result, and returns three figures whose captions and
page numbers are all correct. The images are not:

- Figure 15.2 "Section of a human heart" — a 472x1136 strip that is mostly
  body text, heart cut off at the bottom
- Figure 15.3 "Diagrammatic presentation of a standard ECG" — a page header
  band reading "BODY FLUIDS AND CIRCULATION"
- Figure 15.4 — a vessel cross-section cut off at the right edge

The cause is the vector extraction pass, which captures page regions rather
than figures: 33% of all 522 figures are taller than 800px, and among the
vector-rendered ones it is 41% against 15% for the original raster pass.
A high score does not predict a good crop, because the score is computed
against the caption.

## Mathematics has almost no figures

5 figures, three of which are chapter-opening pages. "Draw a diagram for
relations and functions" returns Fig. 2.1 at 0.60 — the chapter title page
carrying a portrait of Leibnitz — and it clears the 0.55 floor, so it is shown
as though it were a diagram. Avoid maths diagram questions.

## The YouTube persona only appears under Physics

Both registered educators are physics: "Class 11 Physics (YouTube lecture)"
(360 passages) and "Walter Lewin (MIT 8.02)" (34 passages), both Ready. The
panel filters by subject, so on Biology or Chemistry it correctly says "No
educators for <subject> yet" and the dropdown is empty. Switch to Physics
before showing it. That is almost certainly why it looked missing.

**Demo it with Walter Lewin and an electromagnetism question**, because the
style is only applied when at least five transcript passages match:

| Persona | Ask | Result |
|---|---|---|
| Walter Lewin (MIT 8.02) | Explain electric flux and Gauss law. | applied=True |
| Walter Lewin (MIT 8.02) | What is an electric field? | applied=True |
| Class 11 Physics (YouTube) | Explain units and dimensional analysis. | applied=False |

The third is worth knowing: the Hindi lecture persona does not reach the
threshold even on its own topic, so the answer comes back in standard style
with a line explaining why. That is the designed behaviour, not a fault, but
it is not what you want on screen during a review.

## The language selector answers in English on purpose

Ask in Hindi, Kannada or Tamil and the answer comes back in English with a
line saying the language is not available on this install. That is deliberate.
Neither local model can write these languages: asked to define refraction,
qwen2.5:7b produced a transliteration rather than the real Hindi term, and
fluent nonsense in Kannada and Tamil. Through the full prompt a Hindi answer
came back containing neither the word for refraction nor the word for light.
The grounding audit scored it 1.0, because it matches against English passages
and cannot read Devanagari, so nothing downstream catches it.

To turn it on, set `LLM_MULTILINGUAL_MODEL` in `.env` to a capable model —
`openrouter:<model>` works and an OpenRouter key is already configured.
Test it before relying on it.

## Telegram needs credentials

Not configured: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` are empty
and the webhook returns `503 Telegram is not configured.` The code is
complete — commands and LaTeX-to-Unicode formatting were both tested offline
and work. See [telegram-setup.md](telegram-setup.md); it needs a BotFather
token and a public HTTPS tunnel, so allow time before the review.
