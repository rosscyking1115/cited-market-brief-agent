"""Reader-mode translations for approved/live briefs.

Translations are a sidecar convenience layer. The English generated draft remains
the canonical cited artifact for audit, review, and exports.
"""

import json
import logging
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from app.briefs.generator import _json_payload
from app.core.config import settings

Locale = Literal["zh-Hant", "ko"]
logger = logging.getLogger(__name__)

LOCALE_NAMES: dict[str, str] = {
    "zh-Hant": "Traditional Chinese",
    "ko": "Korean",
}


class TranslatedSection(BaseModel):
    title: str
    content_markdown: str


class BriefTranslation(BaseModel):
    locale: Locale
    label: str
    disclaimer: str = Field(
        description="Short note explaining that English remains the source of record."
    )
    sections: list[TranslatedSection] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


SYSTEM_PROMPT = """You translate audit-ready investment research briefs for family readers.

Rules:
- Translate into the requested language using clear, professional financial-news style.
- Preserve every citation marker exactly, including [#0], [#1], [C-000](#evidence-ledger).
- Preserve company tickers, CIKs, form names, dates, percentages, and units.
- Do not add new facts, opinions, recommendations, or investment advice.
- Do not translate inside citation markers.
- Output ONLY valid JSON matching the requested schema."""


def _loads_translation_payload(raw: str) -> dict:
    text = _json_payload(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            raise
        payload, _ = json.JSONDecoder().raw_decode(text[start:])
        if not isinstance(payload, dict):
            raise
        return payload


def translate_brief_payload(locale: Locale, draft: dict) -> BriefTranslation:
    import litellm  # noqa: PLC0415

    label = LOCALE_NAMES[locale]
    payload = {
        "locale": locale,
        "target_language": label,
        "sections": draft.get("brief_sections", []),
        "open_questions": draft.get("open_questions", []),
    }
    response = litellm.completion(
        model=settings.generation_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Translate this brief payload. Return JSON with keys: locale, label, "
                    "disclaimer, sections, open_questions. The sections array must keep "
                    "the same length and order, and each section must contain title and "
                    "content_markdown.\n\n"
                    f"{json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=5000,
        request_timeout=settings.translation_request_timeout_seconds,
    )
    raw = response["choices"][0]["message"]["content"]
    translated_payload = _loads_translation_payload(raw)
    translated_payload["locale"] = locale
    translated_payload["label"] = label
    return BriefTranslation.model_validate(translated_payload)


def cached_translation(draft: dict, locale: str) -> dict | None:
    cached = draft.get("_translations", {}).get(locale)
    return cached if isinstance(cached, dict) else None


def with_cached_translation(draft: dict, locale: Locale) -> tuple[dict, dict]:
    cached = cached_translation(draft, locale)
    if cached:
        return draft, cached

    translation = translate_brief_payload(locale, draft).model_dump()
    translations = {**draft.get("_translations", {}), locale: translation}
    return {**draft, "_translations": translations}, translation


def prewarm_brief_translations(
    draft: dict,
    locales: Iterable[Locale] = ("zh-Hant", "ko"),
) -> dict:
    """Best-effort sidecar translation cache for reader mode.

    The English draft remains canonical. Translation failures should not block
    brief creation; the API route can still retry a missing locale on demand.
    """
    next_draft = dict(draft)
    for locale in locales:
        try:
            next_draft, _translation = with_cached_translation(next_draft, locale)
        except Exception:
            logger.exception("Failed to prewarm %s translation", locale)
    return next_draft
