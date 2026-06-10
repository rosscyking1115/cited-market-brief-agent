"""SEC EDGAR connector.

Fair-access compliance (launch no-go gate):
- Declared User-Agent is REQUIRED (settings.sec_user_agent) — refuse to run without it.
- Hard ceiling 10 req/s; we throttle to settings.sec_max_requests_per_second (default 8).
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

Phase 1 note: prefer `edgartools` for typed filing access (HTML/XBRL native);
this client covers the raw data.sec.gov JSON endpoints and enforces fair access
for anything edgartools does not wrap.
"""

import asyncio
import time

import httpx

from app.core.config import settings

BASE_DATA = "https://data.sec.gov"
BASE_WWW = "https://www.sec.gov"


class FairAccessThrottle:
    """Simple async rate limiter keeping us under the EDGAR ceiling."""

    def __init__(self, max_per_second: float) -> None:
        self._min_interval = 1.0 / max_per_second
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delta = now - self._last_request
            if delta < self._min_interval:
                await asyncio.sleep(self._min_interval - delta)
            self._last_request = time.monotonic()


class SecEdgarClient:
    def __init__(self) -> None:
        if not settings.sec_user_agent.strip():
            raise RuntimeError(
                "SEC_USER_AGENT is required (format: 'App Name contact@example.com'). "
                "EDGAR fair-access policy mandates a declared User-Agent."
            )
        self._throttle = FairAccessThrottle(settings.sec_max_requests_per_second)
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    async def _get_json(self, url: str) -> dict:
        await self._throttle.wait()
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    async def get_submissions(self, cik: str) -> dict:
        """Filing index for a company. CIK is zero-padded to 10 digits."""
        cik10 = str(int(cik)).zfill(10)
        return await self._get_json(f"{BASE_DATA}/submissions/CIK{cik10}.json")

    async def get_company_facts(self, cik: str) -> dict:
        """XBRL company facts (financial data points with units and periods)."""
        cik10 = str(int(cik)).zfill(10)
        return await self._get_json(f"{BASE_DATA}/api/xbrl/companyfacts/CIK{cik10}.json")

    async def get_company_tickers(self) -> dict:
        """Ticker -> CIK mapping maintained by the SEC."""
        return await self._get_json(f"{BASE_WWW}/files/company_tickers.json")

    async def get_raw(self, url: str) -> bytes:
        """Fetch a filing document (Archives URL) under the same fair-access throttle."""
        await self._throttle.wait()
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.content

    async def aclose(self) -> None:
        await self._client.aclose()
