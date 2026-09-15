"""Pure derivations from events and curve. No HA imports; easy to test."""

from __future__ import annotations

import math
from bisect import bisect_left
from datetime import datetime, timedelta
from itertools import pairwise
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pyopentides import Point, TideEvent

State = Literal["rising", "falling"]


def bracket(
    events: list[TideEvent], now: datetime
) -> tuple[TideEvent | None, TideEvent | None]:
    """(last event at or before now, first event after now)."""
    times = [e.time for e in events]
    i = bisect_left(times, now)
    # times[i] >= now; treat an event exactly at now as "previous"
    if i < len(events) and events[i].time == now:
        i += 1
    prev = events[i - 1] if i > 0 else None
    nxt = events[i] if i < len(events) else None
    return prev, nxt


def state(events: list[TideEvent], now: datetime) -> State | None:
    _, nxt = bracket(events, now)
    if nxt is None:
        return None
    return "rising" if nxt.kind == "high" else "falling"


def next_of(events: list[TideEvent], kind: str, now: datetime) -> TideEvent | None:
    for e in events:
        if e.time > now and e.kind == kind:
            return e
    return None


def cosine_between(a: TideEvent, b: TideEvent, t: datetime) -> float:
    """Height at t assuming a cosine between adjacent high/low events."""
    span = (b.time - a.time).total_seconds()
    if span <= 0:
        return a.height_m
    frac = (t - a.time).total_seconds() / span
    mid = (a.height_m + b.height_m) / 2
    amp = (a.height_m - b.height_m) / 2
    return mid + amp * math.cos(math.pi * frac)


def interpolate_curve(curve: list[Point], t: datetime) -> float | None:
    """Linear interpolation on the curve; None if t is outside it."""
    if len(curve) < 2 or not curve[0].time <= t <= curve[-1].time:
        return None
    times = [p.time for p in curve]
    i = bisect_left(times, t)
    if times[i] == t:
        return curve[i].height_m
    a, b = curve[i - 1], curve[i]
    frac = (t - a.time).total_seconds() / (b.time - a.time).total_seconds()
    return a.height_m + (b.height_m - a.height_m) * frac


def predicted_at(
    events: list[TideEvent], curve: list[Point], t: datetime
) -> float | None:
    """Curve if it covers t, else cosine between bracketing events."""
    h = interpolate_curve(curve, t)
    if h is not None:
        return h
    prev, nxt = bracket(events, t)
    if prev is None or nxt is None:
        return None
    return cosine_between(prev, nxt, t)


def window(
    events: list[TideEvent], now: datetime, length: timedelta
) -> list[TideEvent]:
    return [e for e in events if now <= e.time <= now + length]


def downsample(
    curve: list[Point], now: datetime, length: timedelta, step: timedelta
) -> list[Point]:
    """Points within [now, now+length], thinned to roughly ``step``."""
    out: list[Point] = []
    last: datetime | None = None
    for p in curve:
        if p.time < now or p.time > now + length:
            continue
        if last is None or p.time - last >= step:
            out.append(p)
            last = p.time
    return out


# -- range, springs and neaps ------------------------------------------------

SPRING_NEAP_WINDOW = timedelta(days=15)  # a bit over half a synodic month
RATE_STEP = timedelta(minutes=10)


def ranges(events: list[TideEvent]) -> list[tuple[TideEvent, TideEvent, float]]:
    """(earlier, later, |Δheight|) for each consecutive pair of events."""
    return [(a, b, abs(b.height_m - a.height_m)) for a, b in pairwise(events)]


def current_range(events: list[TideEvent], now: datetime) -> float | None:
    """Range of the half-cycle we're in: |next - previous|."""
    prev, nxt = bracket(events, now)
    if prev is None or nxt is None:
        return None
    return abs(nxt.height_m - prev.height_m)


def extreme_range(
    events: list[TideEvent],
    now: datetime,
    window: timedelta = SPRING_NEAP_WINDOW,
    *,
    largest: bool,
) -> tuple[TideEvent, float] | None:
    """The high water with the largest (spring) or smallest (neap) range in
    [now, now + window]. Returns (that high, its range)."""
    best: tuple[TideEvent, float] | None = None
    for a, b, r in ranges(events):
        if not now <= b.time <= now + window:
            continue
        high = a if a.kind == "high" else b
        if best is None or (r > best[1] if largest else r < best[1]):
            best = (high, r)
    return best


def rate(events: list[TideEvent], curve: list[Point], now: datetime) -> float | None:
    """Rate of rise (+) or fall (-) in m/h, from a central difference."""
    before = predicted_at(events, curve, now - RATE_STEP)
    after = predicted_at(events, curve, now + RATE_STEP)
    if before is None or after is None:
        return None
    return (after - before) / (2 * RATE_STEP.total_seconds() / 3600)
