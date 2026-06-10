from app.changes.macro_delta import compute_series_delta

NEW = {"2026-03": "325.8", "2026-04": "326.6", "2026-05": "327.1"}
OLD = {"2026-03": "325.9", "2026-04": "326.6"}


def test_latest_period_delta() -> None:
    d = compute_series_delta("CPIAUCSL", NEW)
    assert d.latest_date == "2026-05"
    assert d.latest_value == 327.1
    assert d.prev_date == "2026-04"
    assert d.change == 0.5
    assert d.change_pct is not None and abs(d.change_pct - 0.1531) < 0.001
    assert d.has_signal


def test_vintage_revisions_detected() -> None:
    d = compute_series_delta("CPIAUCSL", NEW, OLD)
    assert len(d.revisions) == 1
    rev = d.revisions[0]
    assert rev.date == "2026-03"
    assert rev.old_value == 325.9
    assert rev.new_value == 325.8


def test_missing_observations_skipped() -> None:
    d = compute_series_delta("DGS10", {"2026-06-08": "4.18", "2026-06-09": "."})
    # "." (FRED missing marker) must not become the latest value
    assert d.latest_date == "2026-06-08"
    assert d.latest_value == 4.18
    assert d.change is None  # only one valid observation


def test_no_signal_for_single_unchanged_snapshot() -> None:
    d = compute_series_delta("X", {"2026-01": "1.0"}, {"2026-01": "1.0"})
    assert d.change is None
    assert d.revisions == []
    assert not d.has_signal
