"""GDELT DOC 2.0 connector.

GDELT is used only as open-web news discovery: "trending" or "most covered"
proxies. It does not provide publisher readership counts, so callers must not
label results as "most read" unless another licensed source provides that data.
"""

from dataclasses import dataclass

import httpx

from app.core.config import settings

MARKET_QUERY = (
    '(market OR markets OR stocks OR "central bank" OR inflation OR oil OR gold '
    'OR semiconductor OR tariff OR trade OR "earnings")'
)


@dataclass(frozen=True)
class GdeltArticle:
    title: str
    url: str | None
    domain: str
    seendate: str | None
    source_country: str | None
    language: str | None


class GdeltClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=settings.gdelt_request_timeout_seconds)

    def article_list(self, *, timespan: str, max_records: int = 25) -> list[GdeltArticle]:
        resp = self._client.get(
            settings.gdelt_base_url,
            params={
                "query": MARKET_QUERY,
                "mode": "artlist",
                "format": "json",
                "sort": "datedesc",
                "timespan": timespan,
                "maxrecords": str(max_records),
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            return []

        rows: list[GdeltArticle] = []
        seen_urls: set[str] = set()
        for raw in articles:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or "").strip() or None
            if not title or (url and url in seen_urls):
                continue
            if url:
                seen_urls.add(url)
            rows.append(
                GdeltArticle(
                    title=title,
                    url=url,
                    domain=str(raw.get("domain") or "").strip() or "GDELT",
                    seendate=str(raw.get("seendate") or "").strip() or None,
                    source_country=str(raw.get("sourcecountry") or "").strip() or None,
                    language=str(raw.get("language") or "").strip() or None,
                )
            )
        return rows

    def close(self) -> None:
        self._client.close()
