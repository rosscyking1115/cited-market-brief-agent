"""FRED / ALFRED connector.

- API key required (settings.fred_api_key): https://fred.stlouisfed.org/docs/api/fred/overview.html
- Terms: attribution required in exports; some series carry third-party copyright
  restrictions — store license notes per source. https://fred.stlouisfed.org/docs/api/terms_of_use.html
- Vintage awareness (plan §7): pass realtime_start/realtime_end to retrieve the data
  as it existed at a point in time (ALFRED) — required for honest "macro delta" claims.
"""

import httpx

from app.core.config import settings

BASE = "https://api.stlouisfed.org/fred"


class FredClient:
    def __init__(self) -> None:
        if not settings.fred_api_key.strip():
            raise RuntimeError("FRED_API_KEY is required for the FRED connector.")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _get(self, path: str, **params: str) -> dict:
        resp = await self._client.get(
            f"{BASE}/{path}",
            params={"api_key": settings.fred_api_key, "file_type": "json", **params},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_series_info(self, series_id: str) -> dict:
        """Series metadata: title, units, frequency, seasonal adjustment, last updated."""
        return await self._get("series", series_id=series_id)

    async def get_observations(
        self,
        series_id: str,
        observation_start: str | None = None,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> dict:
        """Observations; realtime_* params pin the data vintage (ALFRED)."""
        params: dict[str, str] = {"series_id": series_id}
        if observation_start:
            params["observation_start"] = observation_start
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        return await self._get("series/observations", **params)

    async def aclose(self) -> None:
        await self._client.aclose()
