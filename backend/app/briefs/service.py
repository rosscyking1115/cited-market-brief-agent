"""Brief orchestration: retrieve -> evidence pack -> generate -> validate ->
persist -> export. Synchronous in Phase 1; Hatchet-wrapped when schedules land.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.briefs.generator import generate_brief_json, llm_available
from app.briefs.guardrails import apply_guardrails
from app.briefs.markdown import build_citation_manifest, render_markdown
from app.briefs.schemas import EvidenceItem
from app.briefs.translation import prewarm_brief_translations, translation_model
from app.briefs.validator import validate_claims
from app.core.config import settings
from app.db.models import (
    Brief,
    Citation,
    Claim,
    ClaimType,
    Export,
    Source,
    SupportStatus,
    Watchlist,
)
from app.rag.retrieval import RetrievedChunk, hybrid_search
from app.services.audit import record_event

_PACK_LIMIT = 24
_VALID_CLAIM_TYPES = {t.value for t in ClaimType}


def _doc_label(chunk: RetrievedChunk, publisher: str) -> str:
    label = f"{publisher} {chunk.doc_type}"
    if chunk.accession:
        label += f" {chunk.accession}"
    if chunk.section:
        label += f" · {chunk.section}"
    return label


def _priority_chunks(db: Session, watchlist: Watchlist, ids: list[str]) -> dict[str, RetrievedChunk]:
    """Load change-detected chunks directly (they outrank retrieval — the brief is
    'what changed', so changed spans lead the evidence pack)."""
    from app.db.models import Chunk, Document

    out: dict[str, RetrievedChunk] = {}
    if not ids:
        return out
    uuids = []
    for sid in ids:
        try:
            uuids.append(uuid.UUID(sid))
        except ValueError:
            continue
    rows = db.execute(
        select(Chunk, Document)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_(uuids), Chunk.org_id == watchlist.org_id)
    ).all()
    for chunk, document in rows:
        out[str(chunk.id)] = RetrievedChunk(
            chunk_id=chunk.id,
            document_id=document.id,
            text=chunk.text,
            section=chunk.section,
            span_start=chunk.span_start,
            span_end=chunk.span_end,
            doc_type=document.doc_type,
            accession=document.filing_accession,
            source_id=document.source_id,
            score=1.0,
        )
    return out


def build_evidence_pack(
    db: Session, watchlist: Watchlist, priority_chunk_ids: list[str] | None = None
) -> tuple[list[EvidenceItem], dict[str, RetrievedChunk], dict[str, str]]:
    """Changed chunks first, then one retrieval per topic; dedupe into a capped pack."""
    changed = _priority_chunks(db, watchlist, priority_chunk_ids or [])

    topics = [f"{t} latest filing risk factors results developments" for t in watchlist.tickers]
    topics += [f"{m} latest observations change" for m in watchlist.macro_series]

    by_id: dict[str, RetrievedChunk] = dict(list(changed.items())[:_PACK_LIMIT])
    for topic in topics:
        for chunk in hybrid_search(db, watchlist.org_id, topic, k=4):
            by_id.setdefault(str(chunk.chunk_id), chunk)
            if len(by_id) >= _PACK_LIMIT:
                break
        if len(by_id) >= _PACK_LIMIT:
            break

    publishers = {
        s.id: s.publisher
        for s in db.scalars(
            select(Source).where(Source.id.in_({c.source_id for c in by_id.values()}))
        )
    }

    pack: list[EvidenceItem] = []
    labels: dict[str, str] = {}
    for span_id, chunk in by_id.items():
        label = _doc_label(chunk, publishers.get(chunk.source_id, ""))
        if span_id in changed:
            label += " (CHANGED vs prior filing)"
        labels[span_id] = label
        pack.append(
            EvidenceItem(span_id=span_id, doc_label=label, section=chunk.section, text=chunk.text)
        )
    return pack, by_id, labels


def generate_and_store_brief(db: Session, watchlist: Watchlist) -> Brief:
    from app.changes.service import changes_since_last_brief

    changes = changes_since_last_brief(db, watchlist)
    pack, chunks_by_id, span_labels = build_evidence_pack(
        db, watchlist, priority_chunk_ids=changes.get("changed_chunk_ids", [])
    )
    model_used = settings.generation_model if llm_available() else "deterministic/extractive-v1"

    generated = generate_brief_json(watchlist.name, pack)
    validations = validate_claims(
        generated.claims, {sid: c.text for sid, c in chunks_by_id.items()}
    )
    validations = apply_guardrails(generated.claims, validations)

    brief = Brief(
        org_id=watchlist.org_id,
        watchlist_id=watchlist.id,
        template=watchlist.template,
        generated_draft=generated.model_dump(),
        status="draft",
    )
    db.add(brief)
    db.flush()

    for i, gen_claim in enumerate(generated.claims):
        validation = next(v for v in validations if v.claim_index == i)
        claim_type = (
            gen_claim.claim_type
            if gen_claim.claim_type in _VALID_CLAIM_TYPES
            else ClaimType.FACTUAL_SUMMARY.value
        )
        claim = Claim(
            org_id=watchlist.org_id,
            brief_id=brief.id,
            text=gen_claim.text,
            claim_type=ClaimType(claim_type),
            confidence=gen_claim.confidence,
            support_status=SupportStatus(validation.support_status)
            if validation.support_status in {s.value for s in SupportStatus}
            else SupportStatus.FLAGGED,
            needs_review=validation.needs_review,
        )
        db.add(claim)
        db.flush()

        for cit in validation.citations:
            chunk = chunks_by_id.get(cit.span_id)
            if chunk is None:
                continue
            db.add(
                Citation(
                    org_id=watchlist.org_id,
                    claim_id=claim.id,
                    chunk_id=chunk.chunk_id,
                    span_start=chunk.span_start,
                    span_end=chunk.span_end,
                    source_url="",
                    evidence_quote=gen_claim.evidence_quote,
                    validator_status=cit.status,
                    validated_at=datetime.now(UTC),
                )
            )

    record_event(
        db,
        org_id=watchlist.org_id,
        action="brief.generated",
        object_type="brief",
        object_id=str(brief.id),
        model_provider=model_used.split("/")[0],
        model_version=model_used,
        prompt_version=settings.prompt_version,
        source_ids=sorted({str(c.source_id) for c in chunks_by_id.values()}),
        detail={
            "claims": len(generated.claims),
            "supported": sum(1 for v in validations if v.support_status == "supported"),
            "flagged": sum(1 for v in validations if v.support_status != "supported"),
            "evidence_spans": len(pack),
        },
    )
    db.commit()
    return brief


def prewarm_and_store_brief_translations(db: Session, brief: Brief) -> None:
    draft = dict(brief.generated_draft or {})
    translated_draft = prewarm_brief_translations(draft)
    if translated_draft == draft:
        return

    brief.generated_draft = translated_draft
    record_event(
        db,
        org_id=brief.org_id,
        action="brief.translations_prewarmed",
        object_type="brief",
        object_id=str(brief.id),
        model_provider="litellm",
        model_version=translation_model(),
        detail={"locales": sorted(translated_draft.get("_translations", {}).keys())},
    )
    db.commit()


def _stored_spans(
    db: Session, generated_claims: list, org_id: uuid.UUID
) -> tuple[dict[str, str], dict[str, str], dict[str, dict]]:
    """Resolve span_ids referenced by the stored draft directly from the chunks table
    (never re-retrieve at export time — the audit artifact must match what was cited)."""
    from app.db.models import Chunk, Document

    span_ids: set[uuid.UUID] = set()
    for claim in generated_claims:
        for sid in claim.citations:
            try:
                span_ids.add(uuid.UUID(sid))
            except ValueError:
                continue
    if not span_ids:
        return {}, {}, {}

    rows = db.execute(
        select(Chunk, Document, Source)
        .join(Document, Document.id == Chunk.document_id)
        .join(Source, Source.id == Document.source_id)
        .where(Chunk.id.in_(span_ids), Chunk.org_id == org_id)
    ).all()

    texts: dict[str, str] = {}
    labels: dict[str, str] = {}
    meta: dict[str, dict] = {}
    for chunk, document, source in rows:
        sid = str(chunk.id)
        texts[sid] = chunk.text
        label = f"{source.publisher} {document.doc_type}"
        if document.filing_accession:
            label += f" {document.filing_accession}"
        if chunk.section:
            label += f" · {chunk.section}"
        labels[sid] = label
        meta[sid] = {
            "doc_type": document.doc_type,
            "accession": document.filing_accession,
            "section": chunk.section,
            "span": [chunk.span_start, chunk.span_end],
            "source_url": source.url,
            "retrieved_at": source.retrieved_at.isoformat() if source.retrieved_at else None,
            "checksum_sha256": source.checksum_sha256,
        }
    return texts, labels, meta


def export_brief_markdown(db: Session, brief: Brief, watchlist: Watchlist) -> tuple[str, str]:
    """Render Markdown + citation manifest, persist export rows, return (md, manifest)."""
    from app.briefs.schemas import GeneratedBrief  # local import avoids cycle confusion

    generated = GeneratedBrief.model_validate(brief.generated_draft)
    span_texts, span_labels, span_meta = _stored_spans(db, generated.claims, watchlist.org_id)
    validations = apply_guardrails(
        generated.claims, validate_claims(generated.claims, span_texts)
    )
    model_used = settings.generation_model if llm_available() else "deterministic/extractive-v1"

    md = render_markdown(
        title="What changed since yesterday?",
        watchlist_name=watchlist.name,
        brief=generated,
        validations=validations,
        span_labels=span_labels,
        model=model_used,
        prompt_version=settings.prompt_version,
        generated_at=brief.created_at,
    )
    manifest = build_citation_manifest(
        brief_id=str(brief.id),
        watchlist_name=watchlist.name,
        brief=generated,
        validations=validations,
        span_meta=span_meta,
        model=model_used,
        prompt_version=settings.prompt_version,
        generated_at=brief.created_at,
    )

    out_dir = Path(settings.exports_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"brief_{brief.id}.md"
    manifest_path = out_dir / f"brief_{brief.id}.manifest.json"
    md_path.write_text(md, encoding="utf-8")
    manifest_path.write_text(manifest, encoding="utf-8")

    for fmt, key in (("md", str(md_path)), ("json_manifest", str(manifest_path))):
        db.add(
            Export(
                org_id=watchlist.org_id,
                brief_id=brief.id,
                fmt=fmt,
                object_key=key,
                ai_marking_embedded=True,
            )
        )
    record_event(
        db,
        org_id=watchlist.org_id,
        action="export.created",
        object_type="brief",
        object_id=str(brief.id),
        detail={"formats": ["md", "json_manifest"]},
    )
    db.commit()
    return md, manifest
