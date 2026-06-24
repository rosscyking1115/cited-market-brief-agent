"""Multi-source finance RSS connector.

Free, legal RSS feeds from finance/business desks (headline + link only, linking
back to the publisher). Reuters/Bloomberg/FT are paywalled with no free feed —
their headlines surface via GDELT discovery instead, not here.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.connectors.bbc import parse_bbc_rss
from app.core.config import settings

logger = logging.getLogger(__name__)

# (display source, feed url). Multiple feeds per source are deduped by URL.
FINANCE_FEEDS: list[tuple[str, str]] = [
    ("BBC", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("NYT", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("Guardian", "https://www.theguardian.com/uk/business/rss"),
]


@dataclass(frozen=True)
class RssArticle:
    source: str
    title: str
    url: str | None
    published_at: datetime | None
    category: str | None
    summary: str | None


def fetch_finance_feeds(
    feeds: list[tuple[str, str]] | None = None,
    *,
    max_per_feed: int = 20,
) -> list[RssArticle]:
    feeds = feeds or FINANCE_FEEDS
    rows: list[RssArticle] = []
    seen: set[str] = set()
    timeout = settings.bbc_request_timeout_seconds
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for source, url in feeds:
            try:
                response = client.get(url)
                response.raise_for_status()
                articles = parse_bbc_rss(response.content, max_records=max_per_feed)
            except Exception as exc:  # noqa: BLE001 - one bad feed must not sink the rest.
                logger.info("Finance RSS feed failed (%s): %s", source, exc)
                continue
            for article in articles:
                if article.url and article.url in seen:
                    continue
                if article.url:
                    seen.add(article.url)
                rows.append(
                    RssArticle(
                        source=source,
                        title=article.title,
                        url=article.url,
                        published_at=article.published_at,
                        category=article.category,
                        summary=article.summary,
                    )
                )
    return rows
