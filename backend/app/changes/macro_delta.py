"""Macro time-series delta detection with data-vintage awareness (plan §1 wedge).

Two signal types:
- latest_delta: newest observation vs the prior period in the SAME snapshot
- revisions: same observation date, different value across snapshots — the
  ALFRED-style 'the past changed' signal none of the chat tools surface
"""

from dataclasses import dataclass, field


@dataclass
class Revision:
    date: str
    old_value: float
    new_value: float


@dataclass
class SeriesDelta:
    series_id: str
    latest_date: str | None = None
    latest_value: float | None = None
    prev_date: str | None = None
    prev_value: float | None = None
    change: float | None = None
    change_pct: float | None = None
    revisions: list[Revision] = field(default_factory=list)

    @property
    def has_signal(self) -> bool:
        return self.change is not None or bool(self.revisions)


def _parse(value: str | float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # FRED uses "." for missing observations
        return None


def compute_series_delta(
    series_id: str,
    new_observations: dict[str, str | float],
    old_observations: dict[str, str | float] | None = None,
) -> SeriesDelta:
    delta = SeriesDelta(series_id=series_id)

    dated = sorted(
        ((d, _parse(v)) for d, v in new_observations.items() if _parse(v) is not None),
    )
    if len(dated) >= 1:
        delta.latest_date, delta.latest_value = dated[-1]
    if len(dated) >= 2:
        delta.prev_date, delta.prev_value = dated[-2]
        delta.change = round(delta.latest_value - delta.prev_value, 6)
        if delta.prev_value:
            delta.change_pct = round(100.0 * delta.change / abs(delta.prev_value), 4)

    if old_observations:
        for date, old_raw in old_observations.items():
            old_val = _parse(old_raw)
            new_val = _parse(new_observations.get(date))
            if old_val is not None and new_val is not None and old_val != new_val:
                delta.revisions.append(Revision(date=date, old_value=old_val, new_value=new_val))
        delta.revisions.sort(key=lambda r: r.date)

    return delta
