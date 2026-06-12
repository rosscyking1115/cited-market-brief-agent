import sys
from types import SimpleNamespace

from app.briefs.translation import translate_brief_payload


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
