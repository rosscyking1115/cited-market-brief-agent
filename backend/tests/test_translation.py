import sys
from types import SimpleNamespace

import pytest

from app.briefs.translation import (
    BriefTranslation,
    check_translation_shape,
    prewarm_brief_translations,
    translate_brief_payload,
)


def test_translate_brief_payload_preserves_citation_markers(monkeypatch) -> None:
    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": """{
                          "locale": "zh-Hant",
                          "label": "Traditional Chinese",
                          "disclaimer": "英文原文仍為準確來源。",
                          "sections": [
                            {
                              "title": "申報變化",
                              "content_markdown": "NVIDIA 新增出口管制風險 [#0]。"
                            }
                          ],
                          "open_questions": ["毛利率變化的原因是什麼？"]
                        }"""
                    }
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    translated = translate_brief_payload(
        "zh-Hant",
        {
            "brief_sections": [
                {
                    "title": "Filing changes",
                    "content_markdown": "NVIDIA added an export-control risk [#0].",
                }
            ],
            "open_questions": ["What drove the gross-margin change?"],
        },
    )

    assert translated.locale == "zh-Hant"
    assert translated.sections[0].title == "申報變化"
    assert "[#0]" in translated.sections[0].content_markdown


def test_translate_brief_payload_normalizes_model_locale(monkeypatch) -> None:
    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": """{
                          "locale": "ko-KR",
                          "label": "한국어",
                          "disclaimer": "영어 원문이 정확한 기준입니다.",
                          "sections": [
                            {
                              "title": "공시 변화",
                              "content_markdown": "NVIDIA는 수출 통제 위험을 추가했습니다 [#0]."
                            }
                          ],
                          "open_questions": []
                        }"""
                    }
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    translated = translate_brief_payload(
        "ko",
        {
            "brief_sections": [
                {
                    "title": "Filing changes",
                    "content_markdown": "NVIDIA added an export-control risk [#0].",
                }
            ],
            "open_questions": [],
        },
    )

    assert translated.locale == "ko"
    assert translated.label == "Korean"
    assert "[#0]" in translated.sections[0].content_markdown


def test_translate_brief_payload_accepts_prose_wrapped_json(monkeypatch) -> None:
    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": """아래는 번역 JSON입니다.
                        {
                          "locale": "ko",
                          "label": "한국어",
                          "disclaimer": "영어 원문이 정확한 기준입니다.",
                          "sections": [
                            {
                              "title": "공시 변화",
                              "content_markdown": "NVIDIA는 수출 통제 위험을 추가했습니다 [#0]."
                            }
                          ],
                          "open_questions": []
                        }"""
                    }
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    translated = translate_brief_payload(
        "ko",
        {
            "brief_sections": [
                {
                    "title": "Filing changes",
                    "content_markdown": "NVIDIA added an export-control risk [#0].",
                }
            ],
            "open_questions": [],
        },
    )

    assert translated.locale == "ko"
    assert translated.sections[0].title == "공시 변화"


def test_prewarm_brief_translations_caches_both_locales(monkeypatch) -> None:
    calls: list[str] = []

    def fake_completion(**kwargs):
        payload = kwargs["messages"][1]["content"]
        locale = "zh-Hant" if '"locale": "zh-Hant"' in payload else "ko"
        calls.append(locale)
        if locale == "zh-Hant":
            content = """{
              "locale": "zh-Hant",
              "label": "Traditional Chinese",
              "disclaimer": "英文原文仍為準確來源。",
              "sections": [{"title": "申報變化", "content_markdown": "NVIDIA 新增風險 [#0]。"}],
              "open_questions": []
            }"""
        else:
            content = """{
              "locale": "ko",
              "label": "Korean",
              "disclaimer": "영어 원문이 정확한 기준입니다.",
              "sections": [{"title": "공시 변화", "content_markdown": "NVIDIA는 위험을 추가했습니다 [#0]."}],
              "open_questions": []
            }"""
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    draft = {
        "brief_sections": [
            {
                "title": "Filing changes",
                "content_markdown": "NVIDIA added a risk [#0].",
            }
        ],
        "open_questions": [],
    }

    warmed = prewarm_brief_translations(draft)
    warmed_again = prewarm_brief_translations(warmed)

    assert calls == ["zh-Hant", "ko"]
    assert sorted(warmed["_translations"].keys()) == ["ko", "zh-Hant"]
    assert warmed_again == warmed


# --------------------------------------------------------------------------
# Shape enforcement
#
# Every test above this line feeds the parser a stub the test itself wrote, so
# each one verifies plumbing and none verifies the contract SYSTEM_PROMPT states.
# Before these checks existed, a translation that dropped both citation markers,
# dropped a section and invented a gross margin was parsed, schema-validated and
# returned with the brief's review state untouched.
#
# These pin SHAPE only. Nothing here reads meaning, so nothing here makes the
# non-English output evaluated — see the README.
# --------------------------------------------------------------------------

SOURCE_DRAFT = {
    "brief_sections": [
        {"title": "Filing changes", "content_markdown": "NVIDIA added an export-control risk [#0]."},
        {"title": "Macro", "content_markdown": "CPI-U rose in March 2026 [#1]."},
    ],
    "open_questions": ["What drove the gross-margin change?"],
}


def _translation(sections: list[tuple[str, str]], open_questions: list[str] | None = None) -> BriefTranslation:
    return BriefTranslation(
        locale="zh-Hant",
        label="Traditional Chinese",
        disclaimer="英文為準。",
        sections=[{"title": t, "content_markdown": c} for t, c in sections],
        open_questions=open_questions or [],
    )


FAITHFUL = [
    ("申報變化", "NVIDIA 新增出口管制風險 [#0]。"),
    ("總體", "CPI-U 於 2026 年3月上升 [#1]。"),
]


def test_faithful_shape_raises_no_flag() -> None:
    """The control. It must stay green or every failure below proves nothing.

    Note the translation writes the month as a digit — "2026 年3月" — which the
    English source never does. That 3 is licensed because the source names March;
    see `consistency.period_ordinals`. Without that the numeric rule would flag
    every correctly localised date and the check would be useless.
    """
    assert check_translation_shape(SOURCE_DRAFT, _translation(FAITHFUL)) == []


def test_dropped_section_is_flagged_by_section_count() -> None:
    flags = check_translation_shape(SOURCE_DRAFT, _translation(FAITHFUL[:1]))
    assert any(f.startswith("section_count:") for f in flags), flags


def test_reordered_sections_are_flagged_by_marker_position() -> None:
    """Order, not just count — the markers no longer sit in their own section."""
    flags = check_translation_shape(SOURCE_DRAFT, _translation(list(reversed(FAITHFUL))))
    assert not any(f.startswith("section_count:") for f in flags), "count is intact; this is an order defect"
    assert [f for f in flags if f.startswith("citation_markers:")] == [
        "citation_markers: section 0 lost [#0]",
        "citation_markers: section 1 lost [#1]",
    ]


def test_dropped_citation_marker_is_flagged() -> None:
    stripped = [("申報變化", "NVIDIA 新增出口管制風險。"), FAITHFUL[1]]
    flags = check_translation_shape(SOURCE_DRAFT, _translation(stripped))
    assert flags == ["citation_markers: section 0 lost [#0]"]


def test_invented_figure_is_flagged_by_numeric_literals() -> None:
    """The dangerous one: shape intact, a number the English draft never stated."""
    invented = [("申報變化", "NVIDIA 新增風險，毛利率達 92% [#0]。"), FAITHFUL[1]]
    flags = check_translation_shape(SOURCE_DRAFT, _translation(invented))
    assert flags == ["numeric_literals: translation states 92, absent from the source"]


def test_failed_shape_marks_the_translation_rather_than_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """It is returned, flagged.

    Withholding it would be an outage; returning it unmarked is what this whole
    change exists to stop.
    """

    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": """{
                          "locale": "zh-Hant",
                          "label": "Traditional Chinese",
                          "disclaimer": "英文為準。",
                          "sections": [{"title": "申報變化", "content_markdown": "毛利率達 92%。"}],
                          "open_questions": []
                        }"""
                    }
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    translated = translate_brief_payload("zh-Hant", SOURCE_DRAFT)

    assert translated.requires_review is True
    assert translated.sections, "the translation is still returned"
    assert {f.split(":")[0] for f in translated.review_flags} == {
        "section_count",
        "citation_markers",
        "numeric_literals",
    }


def test_clean_translation_is_not_marked(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_completion(**_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": """{
                          "locale": "zh-Hant",
                          "label": "Traditional Chinese",
                          "disclaimer": "英文為準。",
                          "sections": [
                            {"title": "申報變化", "content_markdown": "NVIDIA 新增出口管制風險 [#0]。"},
                            {"title": "總體", "content_markdown": "CPI-U 於 2026 年3月上升 [#1]。"}
                          ],
                          "open_questions": ["毛利率變化的原因是什麼？"]
                        }"""
                    }
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(completion=fake_completion))
    translated = translate_brief_payload("zh-Hant", SOURCE_DRAFT)

    assert translated.requires_review is False
    assert translated.review_flags == []
