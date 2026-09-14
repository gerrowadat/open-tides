"""Shared normalisation helpers. Providers call these before returning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyopentides.models import Point, TideEvent


def ensure_utc(dt: datetime) -> datetime:
    """Require tz-aware; return in UTC."""
    if dt.tzinfo is None:
        msg = "naive datetime"
        raise ValueError(msg)
    return dt.astimezone(UTC)


def normalise_events(
    events: list[TideEvent], start: datetime, end: datetime
) -> list[TideEvent]:
    """Sort ascending, drop duplicates (same time+kind), clip to [start, end]."""
    start, end = ensure_utc(start), ensure_utc(end)
    seen: set[tuple[datetime, str]] = set()
    out: list[TideEvent] = []
    for ev in sorted(events, key=lambda e: e.time):
        if not start <= ev.time <= end:
            continue
        key = (ev.time, ev.kind)
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out


def normalise_points(
    points: list[Point], start: datetime, end: datetime
) -> list[Point]:
    """Sort ascending, drop duplicate times, clip to [start, end]."""
    start, end = ensure_utc(start), ensure_utc(end)
    seen: set[datetime] = set()
    out: list[Point] = []
    for p in sorted(points, key=lambda p: p.time):
        if not start <= p.time <= end or p.time in seen:
            continue
        seen.add(p.time)
        out.append(p)
    return out
