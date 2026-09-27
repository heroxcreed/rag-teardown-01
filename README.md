# rag-teardown-01 — Reproducible RAG Reliability Teardown

> **Read first (scope)**: This report is a *method demonstration sample* of the "AI System Reliability Checkup." The system under test is a demo RAG system (known seeded defects in the chunking/retrieval stages; the generation stage is a rule-based script in the main body and real DeepSeek calls in Appendix D). All conclusions serve only to show *what this evaluation method can detect* and **do not constitute any reliability judgment about any production system — including yours**. The true reliability of your system can only come from an independent checkup of your own system — which is exactly the service this report demonstrates.

## What this is

A reproducible teardown of a demo RAG customer-support system. On 2026-09-27 the demo was tested against `deepseek-chat` (52 questions × 3 runs, temperature 0.7) and three failure signals were caught: **arithmetic hallucination**, **over-refusal**, and **retrieval cascade**. This repo ships 8 of those 52 questions, the exact retrieval code, the deterministic judge, and the recorded answers — so you can re-run the mechanism instead of taking our word for it. The story of each signal is in [NOTES.md](NOTES.md).

## Reproduce in 3 steps

```bash
git clone https://github.com/heroxcreed/rag-teardown-01.git
cd rag-teardown-01

# 1) Inspect without spending a cent: prompts + retrieval, no API calls
python3 teardown/run_teardown.py --dry-run

# 2) Full reproduction (~8 model calls, 1 run per question)
DEEPSEEK_API_KEY=sk-... python3 teardown/run_teardown.py

# 3) Compare your verdicts against the recorded session
#    teardown/data/recorded_run_2026-09-27.json
```

Targeted re-runs: `python3 teardown/run_teardown.py --only C2 --runs 3`, `--only F1,F2`, `--only M2,R1,R2`.

## Requirements

- Python 3.8+, standard library only (no `pip install` needed).
- A DeepSeek API key (`DEEPSEEK_API_KEY`), billed to your own account. The script reads it from the environment, never stores it, never logs it. Without it, only `--dry-run` works.

## The 8 questions (sampling logic)

One reproducible example per signal, plus the nearest controls that keep the interpretation honest — all drawn from the recorded 2026-09-27 session:

| ID | Signal | Role in this teardown |
|----|--------|----------------------|
| C2 | arithmetic hallucination | signal example: correct computation (1299−1169=130), no literal grounding; also documents a corrected eval-side error |
| D3 | arithmetic | control: arithmetic done right (1299×0.9=1169.1); judge marks it grounded for a coincidental reason |
| F1 | over-refusal | signal example: docs list the payment methods, model refused 3/3 |
| F2 | over-refusal | boundary case: answerable from FAQ ("no stores yet"), model refused 3/3 |
| M2 | retrieval cascade | signal example, shape A: weight chunk never retrieved → model abandoned the ranking |
| R1 | retrieval cascade | signal example, shape B: zero evidence chunks → correct answer from parametric memory ("true lucky guess") |
| R2 | retrieval cascade | same shape as R1: key sentence dropped by the chunker, answer still "correct" |
| D1 | judge limitation | control: legitimate unit conversion ("2年"→"24个月") flagged ungrounded — the label needs human review |

## Honesty notes

- 8-question subset of a 52-question session; single model (`deepseek-chat`); single date (2026-09-27); temperature fixed at 0.7.
- `recorded_run_2026-09-27.json` carries the **human-reviewed final verdicts**. Fresh re-runs use the deterministic judge only; run-to-run variation is expected (sampling), the defect patterns were stable across 3 runs in the recorded session.
- One spec correction to know about: the recorded session's first-round verdict for C2 used a wrong expected answer (110, an eval-side arithmetic error); the reviewed final is UNGROUNDED_OK with the correct 130. The judge in this repo uses the corrected spec — so your C2 verdict will match the recorded *final*, not the recorded first-round label.
- Corpus and questions stay in Chinese: this retrieval layer is language-sensitive; translating them changes the results. All company names, products, prices, and secrets are fictional.
- Contact: heroxcreed — heroxcreed275@gmail.com (email only, no calls).
