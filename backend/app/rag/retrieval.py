"""Hybrid retrieval: Postgres FTS + pgvector fused with Reciprocal Rank Fusion
(plan §4: single write path, no external search engine at MVP).

RRF is provider-agnostic and needs no score normalization: each ranking
contributes 1/(K + rank). K=60 is the standard constant.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.rag.embeddings import embed_query

RRF_K = 60
CANDIDATES = 30


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    section: str | None
    span_start: int | None
    span_end: int | None
    doc_type: str
    accession: str | None
    source_id: uuid.UUID
    score: float


def rrf_fuse(rankings: list[list[uuid.UUID]], k: int = RRF_K) -> list[tuple[uuid.UUID, float]]:
    """Fuse multiple ranked ID lists into (id, score) sorted by descending RRF score."""
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _fts_ranking(db: Session, org_id: uuid.UUID, query: str, limit: int) -> list[uuid.UUID]:
    tsquery = func.websearch_to_tsquery("english", query)
    stmt = (
        select(Chunk.id)
        .where(Chunk.org_id == org_id, Chunk.fts.op("@@")(tsquery))
        .order_by(func.ts_rank_cd(Chunk.fts, tsquery).desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def _vector_ranking(
    db: Session, org_id: uuid.UUID, query_vec: list[float], limit: int
) -> list[uuid.UUID]:
    stmt = (
        select(Chunk.id)
        .where(Chunk.org_id == org_id, Chunk.embedding.is_not(None))
        .order_by(Chunk.embedding.cosine_distance(query_vec))
        .limit(limit)
    )
    return list(db.scalars(stmt))


def hybrid_search(
    db: Session, org_id: uuid.UUID, query: str, k: int = 8
) -> list[RetrievedChunk]:
    rankings = [_fts_ranking(db, org_id, query, CANDIDATES)]

    query_vec = embed_query(query)  # None in FTS-only mode
    if query_vec is not None:
        rankings.append(_vector_ranking(db, org_id, query_vec, CANDIDATES))

    fused = rrf_fuse(rankings)[:k]
    if not fused:
        return []

    score_by_id = dict(fused)
    rows = db.execute(
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.text,
            Chunk.section,
            Chunk.span_start,
            Chunk.span_end,
            Document.doc_type,
            Document.filing_accession,
            Document.source_id,
            cast(0.0, Float),
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_(score_by_id.keys()))
    ).all()

    out = [
        RetrievedChunk(
            chunk_id=r[0],
            document_id=r[1],
            text=r[2],
            section=r[3],
            span_start=r[4],
            span_end=r[5],
            doc_type=r[6],
            accession=r[7],
            source_id=r[8],
            score=score_by_id[r[0]],
        )
        for r in rows
    ]
    out.sort(key=lambda c: c.score, reverse=True)
    return out
