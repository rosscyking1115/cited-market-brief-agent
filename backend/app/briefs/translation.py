"""Reader-mode translations for approved/live briefs.

Translations are a sidecar convenience layer. The English generated draft remains
the canonical cited artifact for audit, review, and exports.

Their **fidelity is unevaluated**: nothing here or anywhere measures whether a
translation says what the English said, or whether a citation still supports its
claim once both are read in the target language. `check_translation_shape` below
enforces the structural part of the contract `SYSTEM_PROMPT` states — section
count and order, citation markers, no invented numerals — and that is all it
does. A translation that passes every check may still be wrong.
"""

import json
import logging
import re
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field

from app.briefs.consistency import period_ordinals, span_numbers
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
    disclaimer: str = Field(description="Short note explaining that English remains the source of record.")
    sections: list[TranslatedSection] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    requires_review: bool = Field(
        default=False,
        description="True when a shape check failed. The translation is still returned; it is marked, not withheld.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="Names of the shape rules this translation failed, with detail. Empty when it passed.",
    )


SYSTEM_PROMPT = """You translate audit-ready investment research briefs for family readers.

Rules:
- Translate into the requested language using clear, professional financial-news style.
- Preserve every citation marker exactly, including [#0], [#1], [C-000](#evidence-ledger).
- Preserve company tickers, CIKs, form names, dates, percentages, and units.
- Do not add new facts, opinions, recommendations, or investment advice.
- Do not translate inside citation markers.
- Output ONLY valid JSON matching the requested schema."""


# --------------------------------------------------------------------------
# Enforcing the contract the prompt above already states
#
# The prompt demands preserved citation markers and a sections array of the same
# length and order. Until these checks existed nothing verified any of it: a
# translation that dropped both markers, dropped a section and asserted a margin
# the English draft never mentioned was parsed, validated against the schema and
# returned normally, with the brief's review state untouched.
#
# That is attestation, not enforcement, in a project whose entire subject is
# whether a stated thing is actually supported.
#
# These are SHAPE checks and nothing more. They do not read meaning, so they are
# not a translation evaluation and must never be described as one — the fidelity
# of the non-English output remains unmeasured. Conflating a shape guarantee with
# an evaluation would be precisely the defect this repository exists to name.
# --------------------------------------------------------------------------

#: Both marker forms the prompt names: `[#0]` in draft sections, `[C-000]` once
#: the markdown export has renumbered them. Canonicalised to the bare index so
#: either form compares equal to the other.
_CITATION_MARKER = re.compile(r"\[#(\d+)\]|\[C-(\d+)\]")


def citation_markers(text: str) -> list[str]:
    """Claim indices referenced by `text`, in order of appearance."""
    return [str(int(m.group(1) or m.group(2))) for m in _CITATION_MARKER.finditer(text)]


def _source_sections(draft: dict) -> list[dict]:
    sections = draft.get("brief_sections", [])
    return [s for s in sections if isinstance(s, dict)]


def check_translation_shape(draft: dict, translation: BriefTranslation) -> list[str]:
    """Return the names of the shape rules this translation failed.

    Three rules, one per clause of the prompt's contract:

    1. `section_count` — the translation has as many sections as the source.
    2. `citation_markers` — every marker in source section *i* appears in
       translated section *i*. Checking position rather than the document as a
       whole is what makes this an order check as well as a presence check.
    3. `numeric_literals` — the translation states no number the source did not,
       allowing the ordinals of periods the source names, because Traditional
       Chinese and Korean render "May 2026" with a digit where English does not.
       See `consistency.period_ordinals`.

    Empty list means the translation kept its shape. It says nothing whatever
    about whether the translation is accurate.
    """
    failures: list[str] = []
    source = _source_sections(draft)

    if len(translation.sections) != len(source):
        failures.append(
            f"section_count: source has {len(source)} sections, translation has {len(translation.sections)}"
        )

    for index, (src, out) in enumerate(zip(source, translation.sections, strict=False)):
        expected = citation_markers(str(src.get("content_markdown", "")))
        present = set(citation_markers(out.content_markdown))
        missing = [marker for marker in dict.fromkeys(expected) if marker not in present]
        if missing:
            failures.append(f"citation_markers: section {index} lost {', '.join('[#' + m + ']' for m in missing)}")

    source_text = " ".join(f"{s.get('title', '')} {s.get('content_markdown', '')}" for s in source) + " ".join(
        str(q) for q in draft.get("open_questions", [])
    )
    translated_text = " ".join(f"{s.title} {s.content_markdown}" for s in translation.sections) + " ".join(
        translation.open_questions
    )

    licensed = span_numbers(source_text) | period_ordinals(source_text)
    invented = sorted(span_numbers(translated_text) - licensed)
    if invented:
        failures.append(f"numeric_literals: translation states {', '.join(invented)}, absent from the source")

    return failures


def translation_model() -> str:
    model = settings.translation_model.strip() or settings.generation_model
    if model.startswith("openai/") and not settings.openai_api_key.strip():
        return settings.generation_model
    if model.startswith("anthropic/") and not settings.anthropic_api_key.strip():
        return settings.generation_model
    return model


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
        model=translation_model(),
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
    translation = BriefTranslation.model_validate(translated_payload)

    # Shape enforcement. A failure marks the translation rather than discarding
    # it: the reader is better served by flagged text than by a silent gap, and
    # raising here would turn a reader-mode convenience into an outage. What it
    # must never do is return looking clean.
    flags = check_translation_shape(draft, translation)
    if flags:
        logger.warning("Translation shape check failed for %s: %s", locale, "; ".join(flags))
    return translation.model_copy(update={"requires_review": bool(flags), "review_flags": flags})


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
