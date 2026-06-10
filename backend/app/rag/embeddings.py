"""Embeddings via LiteLLM (library mode, plan §4).

Graceful degradation: without an embedding-provider key, returns None and the
system runs FTS-only retrieval — the vertical slice works offline. LiteLLM is
imported lazily so dev/test environments without it still import cleanly.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_BATCH = 96


def embeddings_enabled() -> bool:
    return bool(settings.openai_api_key.strip() or settings.anthropic_api_key.strip())


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a list of texts. Returns None when embeddings are not configured."""
    if not texts or not settings.openai_api_key.strip():
        return None

    import litellm  # noqa: PLC0415 — lazy: keep import-time deps minimal

    vectors: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i : i + _BATCH]
        resp = litellm.embedding(
            model=settings.embedding_model,
            input=batch,
            dimensions=settings.embedding_dimensions,
        )
        vectors.extend(item["embedding"] for item in resp["data"])
    return vectors


def embed_query(text: str) -> list[float] | None:
    result = embed_texts([text])
    return result[0] if result else None
