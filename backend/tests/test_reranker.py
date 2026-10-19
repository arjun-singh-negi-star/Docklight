from app.services.reranker import hybrid_rerank


def make_candidate(score, text):
    return {"score": score, "metadata": {"doc_id": "d1", "filename": "f.txt", "chunk_text": text}}


def test_hybrid_rerank_surfaces_lexical_match_over_pure_vector_score():
    # Note: BM25's IDF term is exactly 0 for any term split evenly across
    # just 2 documents (N=2, n=1 -> log(1.5) - log(1.5) == 0), a real but
    # tiny-corpus-only edge case. A realistic candidate pool (several
    # documents, as retrieval actually fetches top_k*3 candidates) avoids it.
    candidates = [
        make_candidate(0.95, "The weather today is sunny and warm."),
        make_candidate(0.90, "Our office is closed on public holidays."),
        make_candidate(0.85, "The cafeteria menu changes every Monday."),
        make_candidate(0.40, "Refunds are processed within 14 days of purchase."),
    ]
    result = hybrid_rerank("refund policy days", candidates, top_k=1, alpha=0.1)
    assert "Refunds" in result[0]["metadata"]["chunk_text"]


def test_hybrid_rerank_respects_top_k():
    candidates = [make_candidate(0.5 + i * 0.01, f"chunk number {i}") for i in range(6)]
    assert len(hybrid_rerank("chunk", candidates, top_k=3)) == 3


def test_hybrid_rerank_handles_empty_input():
    assert hybrid_rerank("anything", [], top_k=3) == []
