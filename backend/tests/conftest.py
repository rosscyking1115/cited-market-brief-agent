"""Test harness defaults.

Settings now load the repo-root ``.env`` regardless of CWD (see
``app.core.config``), which means a developer's real keys and feed flags would
otherwise bleed into the suite and make tests hit BBC/GDELT/FRED/LLM endpoints.
This autouse fixture pins the external integrations off so the suite stays
hermetic and offline — the same environment the tests were written against.
Individual tests that exercise a connector pass payloads directly or monkeypatch
these back on as needed.
"""

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _offline_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "bbc_rss_enabled", False)
    monkeypatch.setattr(settings, "gdelt_enabled", False)
    monkeypatch.setattr(settings, "alpha_vantage_enabled", False)
    monkeypatch.setattr(settings, "fred_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
