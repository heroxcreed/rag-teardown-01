"""Retrieval layer, vendored from the demo RAG system.

This file merges the demo's chunker + retriever into one self-contained,
dependency-free module. Behavior is identical to the demo (same constants,
same deterministic ordering), so retrieval results reproduce exactly.

Documented defects (kept on purpose — the teardown studies them):
  chunking:
    1. fixed 120-char hard splits, overlap=0 — sentences get cut mid-word,
       key numbers land in different chunks than their modifiers;
    2. all whitespace stripped — tables are destroyed, headers misalign;
    3. a trailing short chunk is dropped — end-of-document facts become
       permanently unretrievable.
  retrieval:
    1. literal 2-char shingle overlap only — synonym queries ("运费" vs "邮费")
       score ~0;
    2. no relevance threshold — top-k chunks are returned even when the best
       score is 0, so the generator answers from garbage context.
"""

import os
import re

CHUNK_SIZE = 120
TOP_K = 3
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kb")


def load_documents(kb_dir=KB_DIR):
    docs = []
    for name in sorted(os.listdir(kb_dir)):
        if name.endswith(".md"):
            with open(os.path.join(kb_dir, name), encoding="utf-8") as f:
                docs.append((name, f.read()))
    return docs


def chunk_text(text, chunk_size=CHUNK_SIZE):
    compact = re.sub(r"\s+", "", text)
    chunks = [compact[i:i + chunk_size] for i in range(0, len(compact), chunk_size)]
    if chunks and len(chunks[-1]) < chunk_size:
        chunks.pop()
    return chunks


def build_chunks(kb_dir=KB_DIR):
    result = []
    for doc_id, text in load_documents(kb_dir):
        for i, c in enumerate(chunk_text(text)):
            result.append((doc_id, i, c))
    return result


def _normalize(text):
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text.lower())


def _shingles(text, n=2):
    t = _normalize(text)
    return {t[i:i + n] for i in range(len(t) - n + 1)} if len(t) >= n else set()


def retrieve(question, chunks, top_k=TOP_K):
    """Returns [(score, doc_id, chunk_index, chunk_text)], score desc, then
    document order asc. Deterministic. Returns top_k even if best score is 0."""
    q = _shingles(question)
    scored = []
    for order, (doc_id, idx, ctext) in enumerate(chunks):
        scored.append((len(q & _shingles(ctext)), order, doc_id, idx, ctext))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [(s, doc_id, i, t) for s, _, doc_id, i, t in scored[:top_k]]
