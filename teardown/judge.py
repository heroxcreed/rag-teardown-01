"""Deterministic judge, vendored from the demo's real-model eval.

Rules only — no model calls, no heuristics beyond substring matching.
The judge answers one question: does the answer contain a key fact, and is
that fact present in any retrieved chunk (or document)?

Verdicts:
  GROUNDED_OK        answer has the key fact AND some retrieved text has it
  UNGROUNDED_OK      answer has the key fact but NO retrieved text has it
                     (screening signal only — can be legit reasoning like
                     unit conversion, or a parametric-memory lucky guess;
                     needs human review)
  REFUSED_OK         correctly refused (no answerable fact in docs)
  REFUSED_SUBOPTIMAL refused even though the docs contained the answer
  HALLUCINATED       key fact missing and no refusal
  FABRICATED         answer contains explicitly forbidden content
  OTHER_NEEDS_REVIEW none of the above matched; human review required
  ERROR              the model call failed

Known limitation (demonstrated by teardown question D1): computed or
converted facts ("24 months" from "2 years") are flagged UNGROUNDED_OK
because the literal string never appears in the corpus. The judge also
cannot see relational errors (teardown question C2): the numbers can be
right while the comparison direction is wrong.
"""

REFUSAL_PHRASES = ["不知道", "不清楚", "没有相关", "无法回答", "资料中没有",
                   "不确定", "不了解", "未提及", "没有提到"]


def judge(question, answer, legit_texts):
    if answer is None:
        return "ERROR"
    a = answer
    for f in question.get("forbidden", []):
        if f in a:
            return "FABRICATED"
    must_all = question.get("must_all", [])
    must_any = question.get("must_any", [])
    facts = must_all + must_any
    if not facts:
        refused = any(p in a for p in REFUSAL_PHRASES)
        return "REFUSED_OK" if refused else "OTHER_NEEDS_REVIEW"
    if must_all and not all(f in a for f in must_all):
        has = False
    elif must_any and not any(f in a for f in must_any):
        has = False
    else:
        has = True
    refused = any(p in a for p in REFUSAL_PHRASES)
    if has:
        matched = [f for f in facts if f in a]
        gf = question.get("ground_fact")
        check = [gf] if gf else matched
        grounded = any(s in t for s in check for t in legit_texts)
        return "GROUNDED_OK" if grounded else "UNGROUNDED_OK"
    if refused:
        return "REFUSED_OK" if question.get("refusal_expected") else "REFUSED_SUBOPTIMAL"
    return "HALLUCINATED"
