# Screenshots — every feature and every option

Captured from the running application (frontend on :3000, backend on :8000,
Ollama local models) with `playwright`, at 1440×1000 and 2× device scale. The
result screenshots are real model output against the real index of 8,191
chunks, not mock-ups: where a figure appears, the index actually returned it.

## The whole application

| File | What it shows |
|---|---|
| `01-home.png` | Landing page: the six tools, the four subjects, a worked lens-maker answer with its sources |

## The six tools, empty

Each tool is its own page at `/tools/<slug>`.

| File | Tool |
|---|---|
| `02-tool-ask.png` | Ask a question |
| `02-tool-guided.png` | Guided learning |
| `02-tool-notes.png` | Revision notes |
| `02-tool-past-papers.png` | Past paper review |
| `02-tool-practice.png` | Practice paper |
| `02-tool-study-map.png` | Study map |

## Every option, at every value

**Subject** (4) — changes the retrieval filter and the subject indicator colour:
`03-subject-physics.png`, `-chemistry`, `-mathematics`, `-biology`

**Year** (2): `03-year-1st-puc.png`, `03-year-2nd-puc.png`

**Board** (2): `03-board-karnataka.png`, `03-board-cbse.png`
— the CBSE shot also shows the inline warning that the supplied papers are
Karnataka, so CBSE requests may have no matching sources.

**Response language** (8): `03-language-english.png`, `-hindi`, `-kannada`,
`-tamil`, `-telugu`, `-malayalam`, `-marathi`, `-bengali`
— see the note in [review-demo.md](../review-demo.md): the local models cannot
write these languages, so a non-English request answers in English with an
explicit notice rather than confident nonsense.

**Teaching approach** (6): `03-approach-adapt.png`, `-concise`,
`-step-by-step`, `-analogy`, `-worked-example`, `-guiding-questions`

**Notes format** (3, Revision notes only): `03-notes-format-bullet-points.png`,
`-detailed`, `-quick-revision`

**Map type** (5, Study map only): `03-map-type-concept-map.png`,
`-process-flow`, `-derivation-chain`, `-comparison`, `-classification-tree`

**Total marks** (Practice paper only): `03-practice-marks.png` — 10 to 200

## Working results

| File | What it proves |
|---|---|
| `04-ask-answer.png` | A full answer to a derivation question, maths rendered through KaTeX |
| `04-ask-evidence.png` | The retrieval panel opened: hybrid dense + BM25, the passages behind the answer |
| `04-ask-figure.png` | Biology answer with the real textbook figure (Figure 8.4) and a 100% grounding badge |
| `04-voice-tools.png` | Voice input and output: local Whisper transcription, optional Google TTS |
| `05-guided-result.png` | Guided learning answering with questions instead of the conclusion |
| `05-notes-result.png` | Revision notes for a chapter |
| `05-past-papers-result.png` | Recurring questions across the board papers in the index |
| `05-study-map-result.png` | A rendered mermaid concept map with its retrieved passages |
| `08-practice-paper.png` | A validated practice paper: marks, Bloom levels, internal choice |

## Teaching styles (the YouTube personas)

| File | What it shows |
|---|---|
| `06-personas-physics.png` | Both registered educators, Ready, with their passage counts |
| `06-personas-biology.png` | Correctly empty — the panel filters by subject and both educators are physics |
| `06-persona-applied.png` | Walter Lewin's style applied to an electromagnetism answer |

## Teacher tools

| File | What it shows |
|---|---|
| `07-teacher-locked.png` | The dashboard before the access key is supplied |
| `07-teacher-dashboard.png` | Live analytics, syllabus coverage, persona usage, PDF upload and PYQ import |

## Theme and viewport

| File | What it shows |
|---|---|
| `09-home-dark.png` | Landing page in dark mode |
| `09-ask-dark.png` | Ask a question in dark mode |
| `09-home-mobile.png` | Landing page at 390×844 |
| `09-ask-mobile.png` | Ask a question at 390×844 |
