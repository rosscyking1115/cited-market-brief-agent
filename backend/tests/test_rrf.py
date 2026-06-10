import uuid

from app.rag.retrieval import rrf_fuse

A, B, C, D = (uuid.uuid4() for _ in range(4))


def test_agreement_outranks_single_list_top() -> None:
    # B appears in both rankings; A and C top one list each
    fused = rrf_fuse([[A, B, C], [D, B]])
    order = [item for item, _ in fused]
    assert order[0] == B


def test_single_ranking_preserves_order() -> None:
    fused = rrf_fuse([[A, B, C]])
    assert [item for item, _ in fused] == [A, B, C]


def test_empty_rankings() -> None:
    assert rrf_fuse([]) == []
    assert rrf_fuse([[], []]) == []


def test_scores_are_descending() -> None:
    fused = rrf_fuse([[A, B], [B, C], [C, A]])
    scores = [s for _, s in fused]
    assert scores == sorted(scores, reverse=True)
