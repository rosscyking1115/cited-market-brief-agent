"""BBC RSS connector.

BBC RSS is used only for latest-headline discovery. Public BBC feeds do not
provide readership rankings, so downstream code must never label these rows as
"most read" without a separate BBC licence/API grant.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class BbcArticle:
    title: str
    url: str | None
    published_at: datetime | None
    category: str | None


def _parse_pub_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class BbcRssClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=settings.bbc_request_timeout_seconds)

    def latest(self, *, max_records: int = 20) -> list[BbcArticle]:
        resp = self._client.get(settings.bbc_rss_url)
        resp.raise_for_status()
        return parse_bbc_rss(resp.content, max_records=max_records)

    def close(self) -> None:
        self._client.close()


def parse_bbc_rss(content: bytes, *, max_records: int = 20) -> list[BbcArticle]:
    # RSS metadata only; no entity expansion output is rendered or persisted as trusted content.
    root = ElementTree.fromstring(content)  # noqa: S314
    rows: list[BbcArticle] = []
    seen_urls: set[str] = set()
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip() or None
        if not title or (url and url in seen_urls):
            continue
        if url:
            seen_urls.add(url)
        rows.append(
            BbcArticle(
                title=title,
                url=url,
                published_at=_parse_pub_date(item.findtext("pubDate")),
                category=(item.findtext("category") or "").strip() or None,
            )
        )
        if len(rows) >= max_records:
            break
    return rows
