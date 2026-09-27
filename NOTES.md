# RAG Reliability Teardown 01 — Three Failure Signals, Reproduced

> **Read first (scope)**: This report is a *method demonstration sample* of the "AI System Reliability Checkup." The system under test is a demo RAG system (known seeded defects in the chunking/retrieval stages; the generation stage is a rule-based script in the main body and real DeepSeek calls in Appendix D). All conclusions serve only to show *what this evaluation method can detect* and **do not constitute any reliability judgment about any production system — including yours**. The true reliability of your system can only come from an independent checkup of your own system — which is exactly the service this report demonstrates.

## What was run

On 2026-09-27, a demo RAG customer-support system (fictional company, fictional data) was tested against `deepseek-chat` (temperature 0.7): 52 questions × 3 independent runs. Verdicts went through deterministic rules first, then human review. This repo ships 8 of those 52 questions, the exact retrieval code, the deterministic judge, and the recorded answers verbatim — so you can re-run the mechanism yourself instead of taking our word for it.

## Signal 1 — Arithmetic hallucination (C2)

**Question:** "帐篷的会员价比售价便宜多少？" — how much cheaper is the member price than the selling price?

**Retrieved:** the price-table chunk (selling 1299, member 1169).

**Model, 3/3 runs:** "会员价是1169元，售价比会员价便宜130元（1299元 - 1169元 = 130元）" — the arithmetic 1299−1169=130 is correct.

**How it was caught — and the honest part:** the first-round deterministic verdict was HALLUCINATED, but not because the model failed. The eval spec itself contained the wrong expected answer (110 — an arithmetic error on the evaluation side). Human review caught it, corrected the record to 130, and the final verdict is UNGROUNDED_OK: legitimate reasoning, because the derived number "130" appears in no retrieved chunk. A computed fact has no literal grounding by construction — no keyword judge can verify arithmetic, it can only notice the absence.

**What this demonstrates:** substring judges match strings, not computations. Any number the model derives (rather than copies) will look "ungrounded" to a literal judge, and the eval protocol itself needs the same adversarial review as the model. We documented the correction instead of silently fixing it.

Reproduce: `DEEPSEEK_API_KEY=sk-... python3 run_teardown.py --only C2 --runs 3`

## Signal 2 — Over-refusal (F1; F2 as the boundary case)

**F1 — "可以打白条吗？"** (Can I pay on IOU credit?) The docs explicitly list the supported payment methods — WeChat Pay, Alipay, UnionPay. 白条 is not among them, so the answerable response is "not supported; the supported methods are X."

**Model, 3/3 runs:** refused ("no relevant information"), never cited the payment list. Final verdict: REFUSED_SUBOPTIMAL, stable.

**How it was caught:** the spec marks this question `refusal_expected: false`; the judge detects refusal phrasing; human review confirmed the answer was present in the retrieved context. Refusal is not always wrong — in the same session the model correctly refused to disclose an internal staff discount code — which is why the protocol distinguishes REFUSED_OK from REFUSED_SUBOPTIMAL per question instead of counting refusals.

**F2 — "你们在北京有几家分店？"** The FAQ states there are no physical stores yet ("暂未开设线下门店"). The model refused 3/3 instead of citing that sentence. Same verdict after review. The pattern: when the answer requires *using* a retrieved sentence rather than *finding* one, the model falls back to refusal.

Reproduce: `DEEPSEEK_API_KEY=sk-... python3 run_teardown.py --only F1,F2 --runs 3`

## Signal 3 — Retrieval cascade (M2 and R1/R2: two shapes)

A stage-2 retrieval miss cascading into a stage-3 generation failure — in two opposite shapes.

**Shape A — miss → task failure (M2).** "Rank the three products by weight." The sleeping-bag weight chunk (1.2kg) was never retrieved — a retrieval defect, the fact exists in the corpus. With one of three facts missing, the model abandoned the ranking 3/3 ("weight not in the docs"). Final: REFUSED_SUBOPTIMAL. The honest note: the model did *not* invent a weight. The defect is in retrieval, not in honesty — and a generation-only test would have blamed the wrong stage.

**Shape B — miss → ungrounded answer (R1, R2).** "帐篷内帐用的什么网纱？" The term "尼龙网纱" was split across two chunks by the 120-char hard cut ("20D尼 | 龙网纱"), so no retrieved chunk contained the full word — yet the model answered "20D尼龙网纱" 3/3, correctly, from parametric memory. Final: UNGROUNDED_OK, reviewed as a "true lucky guess." R2 is the same shape: the "7天无理由" sentence was dropped by the chunker's tail-drop defect, and the model still answered "7天." This is the dangerous shape in production: a right-looking answer with zero evidence behind it. The teardown's formal ungrounded-correct definition — fact in the answer ∧ fact in no eligible chunk — is what separates it from a grounded answer, without guessing at "what the model was thinking."

Reproduce: `DEEPSEEK_API_KEY=sk-... python3 run_teardown.py --only M2,R1,R2 --runs 3`

## What the judge cannot see (limitations, stated plainly)

- **D1** — "保修期是24个月还是36个月？" → "24个月." The corpus says "2年." The judge flags UNGROUNDED_OK (no literal "24" in any chunk); human review: the conversion is correct, legitimate reasoning. "Ungrounded" is a screening signal, not a failure label — it needs a human to separate lucky guesses from valid inference.
- **D3** — "1299元，9折券后价？" → "1169.1." The judge says GROUNDED_OK — but only because the chunk happens to contain "1169" (the member price). Right verdict, wrong reason: the grounding is coincidental, the reasoning path (1299×0.9) is not what was matched.

## What this teardown does NOT show

- 8 of 52 questions, one model (`deepseek-chat`), one date (2026-09-27), temperature fixed at 0.7. Re-running will vary run to run — that is expected. What reproduces deterministically is the retrieval layer, the judge, and (via `--dry-run`) the prompts themselves. The defect patterns above were stable across 3 runs in the recorded session; your re-run tests the mechanism, not a headline.
- The corpus and questions stay in Chinese: retrieval here is language-sensitive, and translating them changes the results. The company, products, prices, and secrets in the corpus are fictional.
- This is not an audit standard, and it says nothing about any production system — including yours.
