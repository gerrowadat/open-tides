from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from pyopentides.models import Point, TideEvent
from pyopentides.normalise import ensure_utc, normalise_events, normalise_points

T0 = datetime(2026, 9, 14, tzinfo=UTC)


def test_ensure_utc_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        ensure_utc(datetime(2026, 9, 14))


def test_ensure_utc_converts() -> None:
    plus1 = datetime(2026, 9, 14, 1, tzinfo=timezone(timedelta(hours=1)))
    assert ensure_utc(plus1) == T0


def test_events_sorted_deduped_clipped() -> None:
    evs = [
        TideEvent(T0 + timedelta(hours=6), 1.0, "low"),
        TideEvent(T0, 2.0, "high"),
        TideEvent(T0, 2.0, "high"),
        TideEvent(T0 - timedelta(hours=1), 3.0, "low"),
        TideEvent(T0 + timedelta(days=2), 3.0, "high"),
    ]
    out = normalise_events(evs, T0, T0 + timedelta(days=1))
    assert [(e.time, e.kind) for e in out] == [
        (T0, "high"),
        (T0 + timedelta(hours=6), "low"),
    ]


def test_points_sorted_deduped_clipped() -> None:
    pts = [Point(T0 + timedelta(minutes=10), 1.0), Point(T0, 0.5), Point(T0, 0.5)]
    out = normalise_points(pts, T0, T0 + timedelta(hours=1))
    assert [p.time for p in out] == [T0, T0 + timedelta(minutes=10)]
