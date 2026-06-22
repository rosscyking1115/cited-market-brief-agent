"""NYT Most Popular connector — genuine readership (most-viewed).

Unlike BBC RSS (latest) or GDELT (coverage/volume), the NYT Most Popular API
exposes articles that are actually most-viewed over the last 1/7/30 days, so
results may honestly be labeled "most read / most viewed". We display headline +
link only and link back to nytimes.com, per the NYT developer terms; we never
reproduce article body text. The window is daily, not hourly.
"""

from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class NytArticle:
    title: str
    url: str
    published_at: str | None
    section: str | None


class NytMostPopularClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=settings.nyt_request_timeout_seconds)

    def most_viewed(self, *, period: int = 1, max_records: int = 20) -> list[NytArticle]:
        resp = self._client.get(
            f"{settings.nyt_base_url}/viewed/{period}.json",
            params={"api-key": settings.nyt_api_key},
        )
        resp.raise_for_status()
        return parse_nyt_most_popular(resp.json(), max_records=max_records)

    def close(self) -> None:
        self._client.close()


def parse_nyt_most_popular(payload: object, *, max_records: int) -> list[NytArticle]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []

    rows: list[NytArticle] = []
    seen: set[str] = set()
    for raw in results:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        if not title or not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            NytArticle(
                title=title,
                url=url,
                published_at=str(raw.get("published_date") or "").strip() or None,
                section=str(raw.get("section") or "").strip() or None,
            )
        )
        if len(rows) >= max_records:
            break
    return rows
