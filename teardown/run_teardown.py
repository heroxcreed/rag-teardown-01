#!/usr/bin/env python3
"""Minimal reproducible RAG teardown.

Reproduces the three failure signals from the 2026-09-27 real-model run
(52 questions x 3 runs on deepseek-chat) with a small, documented subset of
8 questions. The retrieval layer (retrieval.py) and the deterministic judge
(judge.py) are byte-identical in behavior to the original demo; only the
model-calling code was rewritten to use a plain DEEPSEEK_API_KEY env var
instead of the original private credential plumbing.

Usage:
    python3 run_teardown.py --dry-run          # no API calls: show prompts + retrieval
    DEEPSEEK_API_KEY=<your-key> python3 run_teardown.py
    DEEPSEEK_API_KEY=<your-key> python3 run_teardown.py --runs 3 --only C2,F1
"""

import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retrieval
from retrieval import build_chunks, retrieve, TOP_K
from judge import judge

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
TEMPERATURE = 0.7
SYSTEM_ROLE = "你是云杉户外用品有限公司的智能客服助手，请根据以下资料回答用户问题："


def build_prompt(q, chunks):
    retrieved = retrieve(q["question"], chunks, top_k=TOP_K)
    context = "\n".join("[%s#%s] %s" % (doc_id, idx, ctext)
                        for _, doc_id, idx, ctext in retrieved)
    legit = [ctext for _, _, _, ctext in retrieved]
    user_prompt = "资料：\n%s\n\n用户问题：%s" % (context, q["question"])
    meta = [{"score": s, "doc": doc_id, "chunk": idx}
            for s, doc_id, idx, _ in retrieved]
    return user_prompt, meta, legit


def call_model(user_prompt, api_key, temperature=TEMPERATURE, retries=3):
    payload = {"model": MODEL,
               "messages": [{"role": "system", "content": SYSTEM_ROLE},
                            {"role": "user", "content": user_prompt}],
               "temperature": temperature, "max_tokens": 512, "stream": False}
    err = "unknown error"
    for attempt in range(retries):
        req = urllib.request.Request(
            API_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + api_key},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            text = msg.get("content") or ""
            if text.strip():
                return text.strip(), None
            err = "empty reply"
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:200]
            time.sleep(3 * (attempt + 1))
    return None, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble prompts and show retrieval; make no API calls")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--only", default=None, help="e.g. C2,F1")
    ap.add_argument("--out", default=os.path.join(HERE, "teardown_results.json"))
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not args.dry_run and not api_key:
        sys.stderr.write(
            "error: DEEPSEEK_API_KEY is not set.\n"
            "  Get a key at https://platform.deepseek.com, then run:\n"
            "    DEEPSEEK_API_KEY=<your-key> python3 run_teardown.py\n"
            "  Or use --dry-run to inspect prompts without any API calls.\n")
        sys.exit(2)

    chunks = build_chunks()
    with open(os.path.join(HERE, "data", "questions.json"), encoding="utf-8") as f:
        questions = json.load(f)
    if args.only:
        want = set(args.only.split(","))
        questions = [q for q in questions if q["id"] in want]
    print("[teardown] chunks=%d questions=%d runs=%d model=%s dry_run=%s"
          % (len(chunks), len(questions), args.runs, MODEL, args.dry_run), flush=True)

    results = []
    for q in questions:
        user_prompt, meta, legit = build_prompt(q, chunks)
        entry = {"id": q["id"], "category": q["category"],
                 "question": q["question"],
                 "teardown_note": q.get("teardown_note", ""),
                 "retrieval": meta, "runs": []}
        if args.dry_run:
            print("\n--- %s %s" % (q["id"], q["question"]))
            for m in meta:
                print("  score=%s %s#%s" % (m["score"], m["doc"], m["chunk"]))
            print("  prompt preview: %s..." % user_prompt[:220].replace("\n", " "))
            results.append(entry)
            continue
        for r in range(args.runs):
            answer, err = call_model(user_prompt, api_key)
            verdict = judge(q, answer, legit)
            entry["runs"].append({"run": r + 1, "answer": answer,
                                  "error": err, "verdict": verdict})
            print("[%s run%d] %s" % (q["id"], r + 1, verdict), flush=True)
        results.append(entry)

    if not args.dry_run:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"meta": {"model": MODEL, "temperature": TEMPERATURE,
                                "runs_per_question": args.runs,
                                "questions": [q["id"] for q in questions]},
                       "results": results}, f, ensure_ascii=False, indent=2)
        print("[teardown] saved -> %s" % args.out)

        print("\n%-4s %-28s %s" % ("ID", "question", "verdicts"))
        for e in results:
            vs = ",".join(r["verdict"] for r in e["runs"])
            print("%-4s %-28s %s" % (e["id"], e["question"][:26], vs))
        print("\nCompare against data/recorded_run_2026-09-27.json "
              "(recorded verdicts from the original 3-run session).")


if __name__ == "__main__":
    main()
