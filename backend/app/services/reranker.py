"""
Hybrid retrieval re-ranking: blends Pinecone's vector similarity score with
a lexical BM25 score over the same candidates, then returns the merged
top_k. Pure semantic search alone often misses exact terms (ids, numbers,
proper nouns); pure keyword search misses paraphrases. Blending both is a
lightweight, well-understood way to get better recall than either alone --
this is a real (if simplified) hybrid-search technique, not a cross-encoder
reranker, and is documented as such.
"""
from rank_bm25 import BM25Okapi


def _normalize(value: float, lo: float, hi: float) -> float:
    return (value - lo) / (hi - lo) if hi > lo else 1.0


def hybrid_rerank(query: str, candidates: list[dict], top_k: int, alpha: float = 0.5) -> list[dict]:
    if not candidates:
        return []

    texts = [c["metadata"]["chunk_text"] for c in candidates]
    tokenized_corpus = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())

    vector_scores = [c["score"] for c in candidates]
    v_lo, v_hi = min(vector_scores), max(vector_scores)
    b_lo, b_hi = min(bm25_scores), max(bm25_scores)

    blended = []
    for candidate, bm25_score in zip(candidates, bm25_scores):
        v_norm = _normalize(candidate["score"], v_lo, v_hi)
        b_norm = _normalize(bm25_score, b_lo, b_hi)
        combined_score = alpha * v_norm + (1 - alpha) * b_norm
        blended.append((combined_score, candidate))

    blended.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _, candidate in blended[:top_k]]
