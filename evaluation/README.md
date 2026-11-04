# Evaluation protocol

The paper's metrics require real evidence. Copy `measurements.example.json`, fill it with measured values, then run `python scripts/evaluation_report.py evaluation/measurements.json`. Empty arrays remain **missing**; the sample is not a successful evaluation.

- Faculty-vet at least 100 questions spanning five semesters/years appropriate to the actual curriculum. Preserve question, generated answer, exact retrieved contexts, reference answer and timing.
- Run RAGAS faithfulness, response relevance and context relevance using a configured evaluator. Record the version, evaluator model and exact rubric; import the measured values. The included report tool does not substitute word overlap for RAGAS.
- For persona consistency, show an independent judge the generated explanation, three genuine educator excerpts and three neutral excerpts. Store each binary style-match outcome as 0 or 1 and validate a stratified subset with faculty.
- Record faculty domain-accuracy judgments, manually verified PYQ trends, formal mock-format compliance and transcription word error rates against labelled audio.
- Collect usefulness and ease-of-use survey scores from at least 30 respondents after at least 14 days of use. Do not infer TAM scores from software tests.
- Preserve all raw measurements and report uncertainty, failure cases, language distribution and hardware. Never enter the target value as a measured result.
