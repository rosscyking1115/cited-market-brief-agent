"""Reader-mode translations for approved/live briefs.

Translations are a sidecar convenience layer. The English generated draft remains
the canonical cited artifact for audit, review, and exports.
"""

import json
from typing import Literal

from pydantic import BaseModel, Field

from app.briefs.generator import _json_payload
from app.core.config import settings

Locale = Literal["zh-Hant", "ko"]

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
    )
    raw = response["choices"][0]["message"]["content"]
    translated = BriefTranslation.model_validate_json(_json_payload(raw))
    return translated.model_copy(update={"locale": locale, "label": label})
